"""탐색 파이프라인(근거 조사 → 라벨링 → 공백 분석 → 반박 검증 → 아이디어 발산 → 반박 검증 → 후보 확정).
메인 파이프라인(00 오케스트레이터)과 별개의 오케스트레이터다. 흐름은 코드, 판단은 에이전트 11~15, 집계와 탈락은 코드(tally).
결과 폴더(discovery_pack/)는 메인 파이프라인의 근거 색인·후보 영역·아이디어 입력이 된다.

  python3 -m cardstudio discover --spec scenarios/genz-discovery/discovery.json --run-id disc-001 [--provider anthropic]"""
from __future__ import annotations

import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor

from . import tally as T
from .agent_runner import AgentRunner, NeedsHuman
from .config import MVP, Settings
from .ensemble import merge_results, variant_prefix
from .events import EventBus
from .evidence import EvidenceStore
from .evidence_build import apply_labels, build_items, merge_scout_results, write_index
from .hitl import HumanGate
from .llm import make_provider

L = lambda p: json.load(open(p, encoding="utf-8"))


def compact_card(c: dict) -> dict:
    return {"id": c["id"], "name": c["name"], "issuer": c["issuer"], "type": c["type"], "tags": c["tags"],
            "headline_benefits": [{k: b.get(k) for k in ("category", "text", "condition")} for b in (c.get("headline_benefits") or [])[:4]],
            "annual_fee_won": c.get("annual_fee_won"), "min_prev_month_spend_won": c.get("min_prev_month_spend_won"),
            "on_sale": c.get("on_sale"), "note": (c.get("note") or "")[:300]}


class Discovery:
    def __init__(self, settings: Settings, run_id: str, spec_path: str, *, provider=None, human: HumanGate | None = None, search=None):
        self.s, self.id = settings, run_id
        self.spec_path = spec_path
        self.spec = L(spec_path)
        self.base = os.path.dirname(os.path.abspath(spec_path))
        self.dir = os.path.join(settings.runs_dir, run_id)
        os.makedirs(self.dir, exist_ok=True)
        self.bus = EventBus(os.path.join(self.dir, "trace.json"))
        self.replay_dir = os.path.join(settings.scenarios_dir, settings.discovery_scenario)
        self.human = human or HumanGate(settings.human_mode, self.bus)
        self.human.bus = self.human.bus or self.bus
        from .tools import make_search
        self.runner = AgentRunner(settings, provider or make_provider(settings.provider, self.replay_dir, settings.region), self.bus, self.dir,
                                  search=search or (make_search() if settings.provider != "replay" else None))
        db = L(os.path.join(self.base, self.spec["competitor_db"]))
        self.cards = db["cards"]
        self.allowed_tags = db["allowed_tags"]
        self.vocab = {"needs": self.spec["vocab"]["needs"], "domains": self.spec["vocab"]["domains"], "tags": self.allowed_tags}
        self.today = self.spec["today"]
        self.counter = 0

    # ---- 공통 ----------------------------------------------------------------------------
    def env(self, agent: str, key: str, question: str, payload: dict) -> dict:
        t = self.spec["target"]
        return {"run_id": self.id, "request_id": f"{self.id}-{key}", "agent": agent, "contract_version": "1.0", "mode": "workflow", "today": self.today,
                "question": question, "output_mode": "json", "depth": "detail",
                "conversation": {"summary": self.spec.get("summary", ""), "segment": t["segment"], "card_type": "신용카드", "period": self.spec.get("period", ""),
                                 "assumptions": self.spec.get("assumptions", []), "own_cards": []},
                "payload": payload}

    def variants(self, agent: str) -> list[dict]:
        """앙상블 변형. replay 이거나 설정이 없으면 단일(None)."""
        specs = self.s.ensembles.get(agent) if self.s.provider != "replay" else None
        if not specs:
            return [{"suffix": "", "provider": None, "model": None, "k": 0}]
        out = []
        for k, sp in enumerate(specs):
            prov, logical = sp.split("/")
            out.append({"suffix": f"@{prov}-{logical}", "provider": make_provider(prov, region=self.s.region), "model": self.s.model_id(agent, logical, prov), "k": k})
        return out

    def run_agent(self, agent: str, stage: str, key: str, question: str, payload_fn, *, id_prefix: str | None = None) -> dict:
        """변형마다 호출하고 합친다. payload_fn(prefix) → payload."""
        vs = self.variants(agent)
        envs = []
        for v in vs:
            pref = variant_prefix(id_prefix, v["k"]) if (id_prefix and len(vs) > 1) else id_prefix
            e = self.runner.call(stage + v["suffix"], agent, self.env(agent, key + v["suffix"].replace("@", "-").replace("/", "-"), question, payload_fn(pref)),
                                 label=f"{agent} {key}{v['suffix']}", provider=v["provider"], model=v["model"])
            envs.append(e)
        return merge_results(agent, envs)

    def par(self, fns: list):
        with ThreadPoolExecutor(max_workers=min(6, max(1, len(fns)))) as ex:
            return [f.result() for f in [ex.submit(fn) for fn in fns]]

    # ---- 실행 ----------------------------------------------------------------------------
    def execute(self) -> dict:
        bus, sp = self.bus, self.spec
        bus.emit("run_start", None, f"탐색 시작: {sp['target']['segment']} (기준일 {self.today})")
        try:
            merged = self.scout()
            store = self.label_and_index(merged)
            gaps = self.analyze_gaps(store)
            ideas = self.ideate(store, gaps)
            return self.finalize(store, merged, gaps, ideas)
        except NeedsHuman as e:
            bus.emit("run_end", None, f"중단: 사람 확인 필요 ({e})")
            raise

    def scout(self) -> dict:
        results = {}

        def one(t):
            def payload(prefix):
                return {"topic": t["topic"], "topic_brief": t["brief"], "target": self.spec["target"], "id_prefix": prefix or t["id_prefix"],
                        "kinds_requested": t.get("kinds", ["facts", "trend_items"]), "min_counts": t.get("min_counts", {}),
                        "search_budget": {"max_queries": t.get("max_queries", 15), "max_fetches": t.get("max_fetches", 12)}}
            results[t["topic"]] = self.run_agent("scout", f"discovery/scout.{t['topic']}", f"scout-{t['topic']}", f"{t['topic']} 주제의 근거를 조사해줘.", payload, id_prefix=t["id_prefix"])
        self.par([lambda t=t: one(t) for t in self.spec["scouts"]])
        merged = merge_scout_results(results)
        self.bus.emit("code", "orchestrator", f"scout {len(results)}주제: 출처 {len(merged['sources'])}, 사실 {len(merged['facts'])}, 트렌드 {len(merged['trend_items'])}, 사례 {len(merged['cases'])}")
        return merged

    def label_and_index(self, merged: dict) -> EvidenceStore:
        items = build_items(merged)
        chunks = [items[i:i + 150] for i in range(0, len(items), 150)]
        labels = {}

        def lab(k, ch):
            def payload(_):
                return {"items": [{k_: it.get(k_) for k_ in ("id", "kind", "text", "age_scope", "topic")} for it in ch], "vocab": self.vocab}
            env = self.run_agent("labeler", f"discovery/label.{k}", f"label-{k}", "근거 항목에 라벨을 붙여줘.", payload)
            labels.update(env["result"]["labels"])
        self.par([lambda k=k, ch=ch: lab(k, ch) for k, ch in enumerate(chunks)])
        labeled, bad = apply_labels(items, labels, self.vocab)
        out = os.path.join(self.dir, "discovery_pack")
        write_index(out, labeled, self.vocab, self.today)
        shutil.copy(os.path.join(self.base, self.spec["competitor_db"]), os.path.join(out, "competitor_db.enriched.json"))
        json.dump({"as_of": self.today, "sources": merged["sources"]}, open(os.path.join(out, "sources.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        self.bus.emit("code", "orchestrator", f"근거 색인 {len(labeled)}항목, 어휘 밖 라벨 {sum(bad.values())}건 제거")
        return EvidenceStore.load(out)

    def slice_focus(self, store: EvidenceStore, focus: dict, k_each: int = 25, cap: int = 140) -> list[dict]:
        seen, out = set(), []
        for need in focus.get("needs") or [None]:
            for e in store.slice(need=need, mechanisms=focus.get("tags", []), domain=None, k=k_each) + \
                     [x for d in focus.get("domains", []) for x in store.slice(need=need, mechanisms=focus.get("tags", []), domain=d, k=10)]:
                if e["id"] not in seen:
                    seen.add(e["id"])
                    out.append(e)
        return out[:cap]

    def constraints(self, store: EvidenceStore) -> list[dict]:
        return [{"id": store.ref(i["id"]), "rule": i["text"]} for i in store.items.values() if i["kind"] == "constraint"]

    # ---- 공백 분석 ------------------------------------------------------------------------
    def analyze_gaps(self, store: EvidenceStore) -> dict:
        sp = self.spec
        cards = [compact_card(c) for c in self.cards]
        all_ids = sorted(store.ids())
        cands = []

        def one(a):
            def payload(prefix):
                return {"angle": {k: a[k] for k in ("id", "title", "description")}, "target": sp["target"], "evidence": self.slice_focus(store, a.get("focus", {})),
                        "competitor_cards": cards, "allowed_tags": self.allowed_tags, "need_labels": sp["vocab"]["needs"], "categories": sp["vocab"]["domains"],
                        "constraints": self.constraints(store), "id_prefix": prefix or a["id_prefix"], "n_candidates": a.get("n", {"min": 4, "max": 7}),
                        "search_available": self.s.provider != "replay" or sp.get("search_available", False), "all_evidence_ids": all_ids}
            env = self.run_agent("gap_analyst", f"discovery/gap.{a['id']}", f"gap-{a['id']}", f"{a['title']} 각도에서 시장 공백 후보를 찾아줘.", payload, id_prefix=a["id_prefix"])
            cands.extend(env["result"]["candidates"])
        self.par([lambda a=a: one(a) for a in sp["angles"]])
        checks = self.critique("gap_candidate", cands, sp.get("lenses_gap", ["existing", "evidence", "risk"]), store, cards, "discovery/crit.gap")
        tl = T.tally(cands, checks, merge=sp.get("merge_gap"), kind="gap")
        self.bus.emit("code", "orchestrator", f"공백 후보 {len(cands)}개 → 유력 {sum(1 for r in tl['ranked'] if r['median'] >= 2)}, 후보 {sum(1 for r in tl['ranked'] if r['median'] < 2)}, 탈락 {sum(1 for r in tl['rows'] if r['dropped'])}")
        return {"candidates": cands, "tally": tl}

    def critique(self, kind: str, subjects: list[dict], lenses: list[str], store: EvidenceStore, cards: list[dict], stage: str) -> dict:
        all_ids = sorted(store.ids())
        evid = [store.compact(i) for i in store.items.values() if i["kind"] in ("fact", "constraint", "trend")]
        out = {}

        def one(lens):
            def payload(_):
                return {"lens": {"id": lens, "title": lens}, "subject_kind": kind, "subjects": subjects, "evidence": evid[:400], "competitor_cards": cards,
                        "constraints": self.constraints(store), "search_available": self.s.provider != "replay" or self.spec.get("search_available", False),
                        "all_evidence_ids": all_ids}
            env = self.run_agent("critic", f"{stage}.{lens}", f"{stage.split('/')[-1]}-{lens}", f"{lens} 렌즈로 반박 검증해줘.", payload)
            out[lens] = [env["result"]["checks"]]
        self.par([lambda l=l: one(l) for l in lenses])
        return out

    # ---- 아이디어 ------------------------------------------------------------------------
    def ideate(self, store: EvidenceStore, gaps: dict) -> dict:
        sp = self.spec
        cards = [compact_card(c) for c in self.cards]
        all_ids = sorted(store.ids())
        by_id = {c["id"]: c for c in gaps["candidates"]}
        gsum = [{"id": r["id"], "title": by_id[r["id"]]["title"], "tier": r.get("tier"), "mechanism_tags": by_id[r["id"]]["mechanism_tags"],
                 "verdict": by_id[r["id"]]["existing_check"]["verdict"], "corrections": r["corrections"][:4]} for r in gaps["tally"]["ranked"]]
        dropped = [{"id": r["id"], "title": by_id[r["id"]]["title"], "reason": ", ".join(r["killed_by"]) + " 렌즈 폐기"} for r in gaps["tally"]["rows"] if r["dropped"]]
        ideas = []

        def one(t):
            def payload(prefix):
                return {"theme": {k: t[k] for k in ("id", "title", "description")}, "pm_directions": sp["pm_directions"], "target": sp["target"],
                        "evidence": self.slice_focus(store, t.get("focus", {}), cap=160) + [store.compact(i) for i in store.items.values() if i["kind"] == "constraint"],
                        "competitor_cards": cards, "allowed_tags": self.allowed_tags, "need_labels": sp["vocab"]["needs"], "gap_candidates": gsum, "dropped": dropped,
                        "constraints": self.constraints(store), "id_prefix": prefix or t["id_prefix"], "n_ideas": t.get("n", {"min": 6, "max": 9}), "all_evidence_ids": all_ids}
            env = self.run_agent("ideator", f"discovery/idea.{t['id']}", f"idea-{t['id']}", f"{t['title']} 테마로 카드 컨셉 아이디어를 내줘.", payload, id_prefix=t["id_prefix"])
            for i in env["result"]["ideas"]:
                i["theme"] = t["title"]
            ideas.extend(env["result"]["ideas"])
        self.par([lambda t=t: one(t) for t in sp["themes"]])
        checks = self.critique("idea", ideas, sp.get("lenses_idea", ["novelty", "evidence", "risk"]), store, cards, "discovery/crit.idea")
        tl = T.tally(ideas, checks, merge=sp.get("merge_idea"), kind="idea")
        self.bus.emit("code", "orchestrator", f"아이디어 {len(ideas)}개 → 순위 {len(tl['ranked'])}, 병합 {len(tl['merge_groups'])}묶음, 탈락 {sum(1 for r in tl['rows'] if r['dropped'])}")
        return {"ideas": ideas, "tally": tl}

    # ---- 마무리 --------------------------------------------------------------------------
    def finalize(self, store, merged, gaps, ideas) -> dict:
        sp = self.spec
        by_idea = {i["id"]: i for i in ideas["ideas"]}
        n = sp.get("finalist_n", 8)
        default = T.default_finalists(ideas["tally"]["ranked"], by_idea, n=n)
        opts = [{"id": r["id"], "label": f"{r['rank']}. {by_idea[r['id']]['name']} (합계 {r['sum']})"} for r in ideas["tally"]["ranked"][:20]]
        d = self.human.ask("HD1", f"데모 후보 {n}개 확정", opts, {"id": "default", "label": "기본안(순위·테마 다양성)", "finalists": default})
        finalists = d.get("finalists") or default
        out = os.path.join(self.dir, "discovery_pack")
        gt = gaps["tally"]
        json.dump({"as_of": self.today, "candidates": [dict(c, **{k: v for k, v in next(r for r in gt["rows"] if r["id"] == c["id"]).items() if k in ("grades", "tier", "rank", "killed_by", "dropped", "merged_into")}) for c in gaps["candidates"]],
                   "method": "렌즈별 등급 중앙값, 어느 렌즈든 폐기면 탈락(tally.py)"}, open(os.path.join(out, "whitespace_candidates.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        it = ideas["tally"]
        json.dump({"as_of": self.today, "ideas": [dict(i, **{k: v for k, v in next(r for r in it["rows"] if r["id"] == i["id"]).items() if k in ("grades", "sum", "killed_by", "dropped", "merged_into", "corrections", "lens_fields")}) for i in ideas["ideas"]],
                   "ranking": [{k: r[k] for k in ("rank", "id", "sum", "grades")} for r in it["ranked"]], "merge_groups": it["merge_groups"], "finalists": finalists},
                  open(os.path.join(out, "ideas_ranked.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        tags = {}
        for fid in finalists:
            for t in by_idea[fid].get("new_tags", []):
                tags.setdefault(t["key"], t)
        json.dump(list(tags.values()), open(os.path.join(out, "new_tag_proposals.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        summary = {"run_id": self.id, "evidence_items": len(store.items), "gap_candidates": len(gaps["candidates"]), "ideas": len(ideas["ideas"]),
                   "finalists": finalists, "new_tags": list(tags), "usage": self.runner.usage_total, "pack": "discovery_pack/"}
        json.dump(summary, open(os.path.join(out, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        self.bus.emit("run_end", None, f"완료. 후보 {len(finalists)}개 확정, 새 태그 {len(tags)}개 제안. 호출 {self.runner.usage_total['calls']}회")
        return summary
