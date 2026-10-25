"""00 E2E 오케스트레이터(코드, LLM 없음). 설계서 agents/00-orchestrator/설계서.md 4절의 노드 순서를 그대로 옮겼다.
역할: 단계 순서, 입력 조립, 하네스 호출, 게이트, 허용된 되돌림, 사람 확인에서 멈춤, 기록. 내용은 만들지 않는다."""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from .agent_runner import AgentRunner, NeedsHuman
from .code_steps import LegacyHarness
from .config import MVP, Settings
from .events import EventBus
from .hitl import HumanGate
from .llm import make_provider
from .llm.replay_provider import PendingStage
from .payloads import Builder
from .tools import CompetitorDB, make_search

# H3: needs_human/fix 항목을 맡을 부서(대기하지 않고 표시만)
CHECK_OWNER = {"G1": "상품기획", "G2": "광고심의", "G3": "법무·준법", "G4": "개인정보보호", "G5": "상품기획", "G6": "재무·리스크"}


class RegressionLimit(Exception):
    pass


class Run:
    """한 번의 실행 상태(RunState). 노드는 멱등이고, 결과는 runs/<id>/<단계>/ 에 남는다."""

    def __init__(self, settings: Settings, run_id: str, request: str):
        self.settings, self.id, self.request = settings, run_id, request
        self.dir = os.path.join(settings.runs_dir, run_id)
        os.makedirs(self.dir, exist_ok=True)
        self.bus = EventBus(os.path.join(self.dir, "trace.json"))
        self.outputs: dict = {}
        self.scope: dict = {}
        self.scenario_data: dict = {}
        self.today = ""
        self.pick: dict | None = None
        self.notes: list[str] = []
        self.areas: list = []           # 05 입력 영역(v2 엔진 결과)
        self.new_tags: list = []        # 조사에서 나온 새 태그 키(시나리오 DB의 new_tag_definitions)
        self.evidence = None           # EvidenceStore | None (시나리오 폴더의 evidence/ 또는 settings.evidence_dir)
        self.evidence_dir = ""
        self.own_issuer = None         # 자사 카드사 이름(시나리오 own_issuer). 있으면 그 카드사 카드는 경쟁 집계에서 빠진다
        self.db_cards, self.allowed_tags, self.db_as_of = [], {}, None
        self.counters = {"regressions": 0, "concept_rework": 0, "adopt_rework": 0, "guardrail_rework": 0}

    def load(self, rel: str):
        return json.load(open(os.path.join(self.dir, rel), encoding="utf-8"))

    def load_opt(self, rel: str):
        p = os.path.join(self.dir, rel)
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None

    def checkpoint(self, node: str):
        json.dump({"run_id": self.id, "node": node, "scope": self.scope, "pick": self.pick, "counters": self.counters,
                   "stages_done": sorted(self.outputs)}, open(os.path.join(self.dir, "state.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)


class Orchestrator:
    def __init__(self, settings: Settings, run_id: str, request: str, *, human: HumanGate | None = None, provider=None, search=None, kb=None):
        self.s = settings
        self.run = Run(settings, run_id, request)
        sc_dir = os.path.join(settings.scenarios_dir, settings.scenario)
        self.legacy = LegacyHarness(self.run.dir, sc_dir)
        self.run.scenario_data = self.legacy.scenario
        self.run.today = self.legacy.scenario["today"]
        self.sc_dir = sc_dir
        ev_dir = settings.evidence_dir or os.path.join(sc_dir, "evidence")      # 시나리오 폴더에 evidence/ 가 있으면 근거 연결 사용
        if os.path.exists(os.path.join(ev_dir, "evidence_index.json")):
            from .evidence import EvidenceStore
            self.run.evidence = EvidenceStore.load(ev_dir)
            self.run.evidence_dir = ev_dir
        dbp = os.path.join(sc_dir, "competitor_db.json")
        if os.path.exists(dbp):         # v2: 시나리오 폴더의 경쟁 카드 DB(50종 + 새 태그)
            d_ = json.load(open(dbp, encoding="utf-8"))
            self.run.db_cards, self.run.allowed_tags, self.run.db_as_of = d_["cards"], d_["allowed_tags"], d_.get("as_of")
            self.run.new_tags = [t["key"] for t in d_.get("new_tag_definitions", [])]
        else:
            d_ = json.load(open(f"{MVP}/samples/03-competitor/in.sample.json", encoding="utf-8"))["payload"]
            self.run.db_cards, self.run.allowed_tags, self.run.db_as_of = d_["competitor_db"]["cards"], d_["allowed_tags"], d_["competitor_db"].get("as_of")
        own = set(self.run.scenario_data.get("own_issuers", []))      # 이 서비스를 쓰는 카드사(자사). 자사 카드는 경쟁 집계에서 빼고 비교 대상으로만 쓴다
        self.run.own_issuer = self.run.scenario_data.get("own_issuer")
        for c in self.run.db_cards:
            c["is_own"] = bool(c.get("is_own")) or c.get("issuer") in own
        if self.run.evidence:
            for c in self.run.evidence.cards:
                c["is_own"] = bool(c.get("is_own")) or c.get("issuer") in own
        self.human = human or HumanGate(settings.human_mode, self.run.bus)
        self.human.bus = self.human.bus or self.run.bus
        db = CompetitorDB(self.run.db_cards)
        self.runner = AgentRunner(settings, provider or make_provider(settings.provider, sc_dir, settings.region, pause=settings.pause_on_missing), self.run.bus,
                                  self.run.dir, legacy=self.legacy,
                                  search=search or (make_search() if settings.provider != "replay" else None), db=db, kb=kb)
        self.b = Builder(self.run)
        self.lim = settings.limits

    # ---- 실행 ----------------------------------------------------------------------------
    def execute(self) -> dict:
        r, bus = self.run, self.run.bus
        bus.emit("run_start", None, f"요청: {r.request} (기준일 {r.today})")
        try:
            self.intake()
            self.h1_scope()
            self.research()
            cells = self.score_cells()
            ws = self.whitespace(cells)
            self.h2_pick(ws)
            winner, twin = self.concept_loop()
            self.h3_legal()
            winner = self.h4_confirm(winner, twin)
            self.design_marketing(winner, twin)
            self.h5_render()
            self.plan_doc()
            result = self.finalize()
        except NeedsHuman as e:
            bus.emit("run_end", None, f"중단: 사람 확인 필요 ({e})")
            r.checkpoint("needs_human")
            raise
        bus.emit("run_end", None, f"완료. 호출 {self.runner.usage_total['calls']}회, 입력 {self.runner.usage_total['input_tokens']} / 출력 {self.runner.usage_total['output_tokens']} 토큰")
        return result

    def regress(self, why: str):
        self.run.counters["regressions"] += 1
        if self.run.counters["regressions"] > self.lim.max_regressions:
            raise RegressionLimit(why)

    def call(self, stage, agent, env, label=""):
        out = self.runner.call(stage, agent, env, label=label)
        self.run.outputs[stage] = out
        self.run.checkpoint(stage)
        return out

    # ---- 노드 ----------------------------------------------------------------------------
    def intake(self):
        """규칙으로 타깃·카드 유형·목표를 뽑는다. 못 뽑은 것만 경량 모델(Haiku)이 해석한다.
        TODO(LLM 보조): 지금은 시나리오 파일의 scope 를 그대로 쓴다."""
        sc = self.legacy.scenario["scope"]
        self.run.scope = {"target_segment": sc["target_segment_name"], "target_segment_id": sc["target_segment"], "card_type": "credit",
                          "target_adopt": sc["target_adopt"], "constraints": sc["constraints"], "allow_invest": bool(sc.get("allow_invest")), "assumptions": self.legacy.scenario["assumptions"]
                          if "assumptions" in self.legacy.scenario else sc.get("assumptions", [])}
        self.run.bus.emit("route", "intake", f"규칙 해석: 타깃 {sc['target_segment_name']}, 목표 채택 의향 {sc['target_adopt']}(가정치)")

    def h1_scope(self):
        d = self.human.ask("H1", "범위 확인", [{"id": "confirm", "label": "그대로 진행"}, {"id": "edit", "label": "범위 수정"}], {"id": "confirm", "label": "그대로 진행"})
        if d.get("id") == "edit" and d.get("scope"):
            self.run.scope.update(d["scope"])

    def research(self):
        """01 시장조사 총괄의 기본 계획: trend ∥ competitor → consumer → 종합.
        TODO(01 LLM화): 01 이 질문별로 추가 호출을 정하는 부분(호출 7·판단 5·240초)은 2차. 지금은 고정 계획."""
        b = self.b
        with ThreadPoolExecutor(max_workers=2) as ex:
            f1 = ex.submit(self.call, "02-trend", "trend", b.trend(), "02 trend (병렬)")
            f2 = ex.submit(self.call, "03-competitor", "competitor", b.competitor(), "03 competitor (병렬)")
            pend = []
            for f in (f1, f2):          # 기록 만들기 모드에서는 둘 다 비어 있을 수 있으니 한꺼번에 모아서 알린다
                try:
                    f.result()
                except PendingStage as e:
                    pend.append(e)
            if pend:
                pend[0].also = [e.stage for e in pend[1:]]
                raise pend[0]
        self.call("04-consumer", "consumer", b.consumer(), "04 consumer (trend 결과 사용)")
        self.call("01-research-lead", "research_lead", b.research_lead(), "01 research_lead 종합")

    def score_cells(self) -> list[dict]:
        if self.s.engine() == "v2":
            cells = self.find_areas()
            c = cells[0]
            self.run.bus.emit("code", "orchestrator", f"find_areas 기회영역 {len(cells)}개, 1순위 {c['seg']}×{c['need']}×{'/'.join(c['mechanisms'])} {c['score']} ({c['type']}, 신뢰도 {c['confidence']})")
            return cells
        cells = self.legacy.score_cells()
        self.run.bus.emit("code", "orchestrator", f"score_cells 기회 점수 상위 {len(cells)}셀, 1순위 {cells[0]['seg']}×{cells[0]['need']} {cells[0]['score']}")
        return cells

    def seed_ideas(self) -> list[dict]:
        """탐색 파이프라인이 확정한 데모 후보(finalists)를 영역 시드로. 등급·참신성 판정·지적 사항을 함께 넘긴다."""
        if not self.run.evidence_dir:
            return []
        p = os.path.join(self.run.evidence_dir, "ideas_ranked.json")
        if not os.path.exists(p):
            return []
        d = json.load(open(p, encoding="utf-8"))
        by = {i["id"]: i for i in d["ideas"]}
        out = []
        for fid in d.get("finalists", []):
            i = by[fid]
            nv = (i.get("lens_fields") or {}).get("novelty", {}).get("novelty_verdict")
            out.append(dict(i, novelty_verdict=nv))
        return out

    def find_areas(self) -> list[dict]:
        from .opportunity import find_areas
        cache = os.path.join(self.sc_dir, "areas.json")        # 기록 시나리오에서는 05 입력이 바뀌지 않도록 첫 계산 결과를 고정한다
        if self.s.provider == "replay" and os.path.exists(cache):
            areas = json.load(open(cache, encoding="utf-8"))
        else:
            o = self.run.outputs
            areas = find_areas(sc=self.legacy.scenario, db_cards=self.run.db_cards, allowed_tags=self.run.allowed_tags,
                               trend=o["02-trend"]["result"]["signals"], consumer=o["04-consumer"]["result"],
                               tensions=o["01-research-lead"]["result"]["conflicts"], ceiling_fn=self.legacy.ceiling_for_tags,
                               target_adopt=self.run.scope["target_adopt"], ideas=self.seed_ideas(),
                               seed_only_tags=set(self.run.new_tags))
            if self.s.provider == "replay" and self.s.pause_on_missing:
                json.dump(areas, open(cache, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(areas, open(f"{self.run.dir}/areas.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        self.run.areas = areas
        return areas

    def whitespace(self, cells: list[dict]) -> dict:
        ok = [c for c in cells if c["feasible"]]
        excluded = [{"seg": c["seg"], "need": c["need"], "reason": f"채택 천장 {c['ceiling']} < 목표 {self.run.scope['target_adopt']}"} for c in cells if not c["feasible"]]
        self.run.bus.emit("gate", "feasibility_gate", f"채택 천장 통과 {len(ok)}/{len(cells)}")
        if not ok:
            self.regress("feasibility")
            raise NeedsHuman("feasibility_gate", [{"code": "GATE_FAILED", "path": "cells", "message": "모든 셀이 목표 채택 의향 미달. H1 에서 범위·목표 재확인 필요"}])
        return self.call("05-whitespace", "whitespace", self.b.whitespace(ok, excluded))

    def h2_pick(self, ws: dict):
        picks = ws["result"]["picks"]
        opts = [{"id": k, "label": f"{p['rank']}순위 {p['seg']}×{p['need']}" + (f"×{'/'.join(p['mechanisms'])}" if p.get("mechanisms") else ""), "choice": k}
                for k, p in enumerate(picks)]
        d = self.human.ask("H2", "기회 선택", opts, opts[0])
        k = d.get("choice", 0)
        self.run.pick = picks[k]
        if k > 0:
            self.run.notes.append(f"H2에서 사람이 1순위 대신 {picks[k]['rank']}순위 셀({picks[k]['seg']}×{picks[k]['need']})을 선택했다.")

    def concept_loop(self):
        """concept → 평가 → 시뮬레이션 → 채택 게이트 → 검증 → 가드레일. 되돌림은 상한 안에서만."""
        r, bus, lim = self.run, self.run.bus, self.lim
        feedback = None
        while True:
            if r.counters["concept_rework"] > lim.concept_rework:
                raise NeedsHuman("concept", [{"code": "GATE_FAILED", "path": "concept_rework", "message": f"재작업 상한 {lim.concept_rework} 초과"}])
            self.call("06-concept", "concept", self.b.concept(r.pick, feedback), "concept 3안" if not feedback else "concept 재작업")
            ev = self.legacy.evaluate()
            top = ", ".join(f"{x['name']}{'✓' if x['pass'] else '✗'}" for x in ev["eval"])
            bus.emit("code", "orchestrator", f"eval_concepts: {top}")
            if not ev["winner"]:
                feedback = {"from": "eval", "target_option": None, "metrics": {"fails": {x["name"]: x["fails"] for x in ev["eval"]}}}
                self.rework("eval 통과 0건", "06-concept", ("in.json", "out.json", "eval.json"))
                continue
            win = ev["winner"]
            twin = self.legacy.simulate()
            bus.emit("code", "orchestrator", f"simulate_twin: 채택 의향 {twin['target_adopt']}, 채택 고객 손익 {twin['adopter_profit']}")
            if twin["target_adopt"] < r.scope["target_adopt"] or twin["adopter_profit"] < twin["behav_floor"]:
                bus.emit("gate", "adopt_gate", f"미달: 채택 {twin['target_adopt']} / 손익 {twin['adopter_profit']}")
                if r.counters["adopt_rework"] >= lim.adopt_rework:
                    raise NeedsHuman("adopt_gate", [{"code": "GATE_FAILED", "path": "adopt", "message": "채택 미달 재작업 상한. 다음 셀로 이동(whitespace 다음 순위)은 2차"}])
                r.counters["adopt_rework"] += 1
                feedback = {"from": "validation", "target_option": win["metrics"]["i"], "metrics": {"adopt": twin["target_adopt"], "topReject": twin["top_reject"]}}
                self.rework("채택 게이트 미달", "06-concept", ("in.json", "out.json", "eval.json"), "07-validation")
                continue
            bus.emit("gate", "adopt_gate", f"통과: {twin['target_adopt']} ≥ {r.scope['target_adopt']}, {twin['adopter_profit']} ≥ {twin['behav_floor']}")
            self.call("07-validation", "validation", self.b.validation(win, twin), "validation 가상 고객 역할극")
            gr = self.call("08-guardrail", "guardrail", self.b.guardrail(win, twin), "guardrail 재무·준법 점검")
            fixes = [c for c in gr["result"]["checks"] if c["status"] == "fix"]
            if fixes and r.counters["guardrail_rework"] < lim.guardrail_rework:
                r.counters["guardrail_rework"] += 1
                feedback = {"from": "guardrail", "target_option": win["metrics"]["i"],
                            "guardrail_fixes": [{"item": c["item"], "suggestion": c["suggestion"]} for c in fixes if c.get("suggestion")],
                            "metrics": {k: win["metrics"][k] for k in ("adopt", "adopterProfit", "cherry", "topReject")},
                            "human_note": "needs_human 항목은 H3에서 담당 부서 지정. 재작업 대상 아님"}
                self.rework(f"가드레일 fix {len(fixes)}건", "06-concept", ("in.json", "out.json", "eval.json"), "07-validation", "08-guardrail")
                continue
            if fixes:
                bus.emit("gate", "guardrail_gate", f"fix {len(fixes)}건 남음. 재작업 상한 소진 → 가장 좋은 시도로 진행하고 09·10 에 미해결로 넘김")
            return win, twin

    def rework(self, why: str, *stages_and_files):
        """되돌림 한 번: 회귀 카운트, 이전 결과 보관, 기록."""
        r = self.run
        r.counters["concept_rework"] += 1
        self.regress(why)
        self.run.bus.emit("rework", "orchestrator", f"concept 재작업 {r.counters['concept_rework']}/{self.lim.concept_rework}: {why}")
        self.runner.archive("06-concept")
        for st in ("07-validation", "08-guardrail"):
            self.runner.archive(st, ("in.json", "out.json", "twin.json"))

    def h3_legal(self):
        gr = self.run.outputs["08-guardrail"]["result"]["checks"]
        todo = [c for c in gr if c["status"] in ("fix", "needs_human")]
        owners = ", ".join(f"{c['id']} {CHECK_OWNER.get(c['id'], '담당 미정')}" for c in todo)
        self.run.bus.emit("human_decision", None, f"H3: {owners} 담당 지정(대기하지 않고 표시)", point="H3", owners={c["id"]: CHECK_OWNER.get(c["id"]) for c in todo})

    def h4_confirm(self, winner, twin):
        d = self.human.ask("H4", f"컨셉 확정: {winner['card']['working_title']}", [{"id": "confirm", "label": "확정"}, {"id": "rework", "label": "재작업 요청"}], {"id": "confirm", "label": "확정"})
        if d.get("id") == "rework":
            raise NeedsHuman("H4", [{"code": "GATE_FAILED", "path": "H4", "message": "재작업 요청: 사유를 feedback.human 으로 concept 재호출(2차 구현)"}])
        return winner

    def design_marketing(self, winner, twin):
        out = self.call("09-design-marketing", "design_marketing", self.b.design_marketing(winner, twin), "design_marketing 전략→보드→스토리보드")
        topics = out["result"].get("needs_research") or []
        if topics and "02-trend-evidence" not in self.run.outputs:   # 1회만 갱신
            self.run.bus.emit("route", "design_marketing", f"needs_research {len(topics)}주제 → trend evidence_pack 1회")
            te = self.call("02-trend-evidence", "trend", self.b.trend_evidence(topics), "trend evidence_pack")
            self.runner.archive("09-design-marketing", ("in.json", "out.json"))
            d = self.b.design_marketing(winner, twin)
            d["payload"]["trend_signals"] += [{k: s[k] for k in ("id", "title", "impl", "reliability", "source_ids") if k in s} for s in te["result"]["signals"]]
            self.call("09-design-marketing", "design_marketing", d, "design_marketing 근거 팩 반영")

    def h5_render(self):
        d = self.human.ask("H5", "스토리보드 미리보기 확인, 렌더 승인", [{"id": "approve", "label": "렌더 승인"}, {"id": "hold", "label": "렌더하지 않음"}], {"id": "approve", "label": "렌더 승인"})
        jobs = self.run.outputs["09-design-marketing"]["result"].get("render_jobs", [])
        self.run.bus.emit("code", "orchestrator", f"렌더 작업 {len(jobs)}건 {'등록' if d.get('id') == 'approve' else '보류'} (렌더러 연결은 2차)")

    def plan_doc(self):
        self.call("10-plan-doc", "plan_doc", self.b.plan_doc(), "plan_doc 7개 섹션 기획서")
        # TODO: backup_requests 중 승인된 것만 해당 파트 자문 1라운드 후 재작성(설계서 10, 상한 1라운드 3건)

    def finalize(self) -> dict:
        r = self.run
        pd = r.outputs["10-plan-doc"]["result"]
        os.makedirs(f"{r.dir}/final", exist_ok=True)
        open(f"{r.dir}/final/기획서.md", "w", encoding="utf-8").write(pd["markdown"])
        summary = {"run_id": r.id, "pick": r.pick, "counters": r.counters, "usage": self.runner.usage_total,
                   "winner": r.load("06-concept/eval.json")["winner"]["metrics"], "twin_adopt": r.load("07-validation/twin.json")["target_adopt"],
                   "files": {"plan_doc_md": "final/기획서.md", "trace": "trace.json"}}
        json.dump(summary, open(f"{r.dir}/final/summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        r.checkpoint("finalize")
        return summary
