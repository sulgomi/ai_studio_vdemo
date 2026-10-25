"""단계별 입력 봉투 조립(코드). 앞 단계 결과에서 받을 필드를 열거해서 넣고 통째로 넘기지 않는다(00 설계서, 각 에이전트 3절).
시나리오 고정 자료(세그먼트 팩, 경쟁사 DB, 점검 항목, 문구 틀)는 scenarios/<이름>/<단계>/in.json 을 틀로 쓴다.
TODO: 틀 파일을 시나리오 팩(scenario_pack/)으로 분리하고 필드별 출처를 스키마에 명시."""
from __future__ import annotations

import copy
import json
import os
import re


class Builder:
    def __init__(self, run):
        self.run = run
        self.n: dict[str, int] = {}

    # -- 공통 ---------------------------------------------------------------------------
    def tpl(self, stage: str) -> dict:
        st = self.run.settings
        for sc in (st.scenario, st.template_scenario):     # 현재 시나리오에 입력 틀이 없으면 틀 시나리오에서 고정 부분을 가져온다
            p = os.path.join(st.scenarios_dir, sc, stage, "in.json")
            if os.path.exists(p):
                return json.load(open(p, encoding="utf-8"))
        raise FileNotFoundError(f"입력 틀 없음: {stage}")

    @property
    def v2(self) -> bool:
        return self.run.settings.scenario != self.run.settings.template_scenario

    def seg_obj(self) -> dict:
        return next(x for x in self.run.scenario_data["segments"] if x["id"] == self.run.scope["target_segment_id"])

    def head(self, stage: str, agent: str, question: str, mode: str = "workflow") -> dict:
        d = copy.deepcopy(self.tpl(stage))
        self.n[agent] = self.n.get(agent, 0) + 1
        d.update(run_id=self.run.id, request_id=f"{self.run.id}-{agent}-r{self.n[agent]}", agent=agent, mode=mode,
                 today=self.run.today, question=question)
        if self.run.notes:
            d["conversation"]["summary"] += " " + " ".join(self.run.notes)
        return d

    def out(self, stage: str) -> dict:
        return self.run.outputs[stage]

    # -- 단계별 -------------------------------------------------------------------------
    def research_lead(self):
        d = self.head("01-research-lead", "research_lead", self.run.request)
        d["payload"]["scope"] = {k: v for k, v in self.run.scope.items() if k != "allow_invest"}   # 01 스코프 스키마는 이 필드를 모른다
        return d

    def trend(self):
        d = self.head("02-trend", "trend", "이번 기획에 쓸 소비·결제·규제 트렌드 시그널을 찾아줘.", "orchestrated")
        store = self.run.evidence
        if store and self.v2:    # 근거 팩 모드: 검색 대신 코드가 고른 출처 문서
            d["payload"].update(pack_mode=True, target=self.run.scope["target_segment"], docs=store.docs(
                lambda it: it.get("relevance") in ("direct", "indirect") and (it.get("topic") or "") in
                ("payment", "card_usage", "policy", "online_shop", "expenditure", "income", "trend", "") and not it.get("stale"), k_sources=24, facts_per_source=5))
        return d

    def competitor(self):
        d = self.head("03-competitor", "competitor", "경쟁 카드의 혼잡한 영역과 빈 영역을 정리해줘.", "orchestrated")
        if self.v2:
            cards = [{"id": c["id"], "name": c["name"], "issuer": c["issuer"], "type": c["type"], "tags": c["tags"], "target": c.get("target", ""),
                      "annual_fee": c.get("annual_fee"), "is_own": bool(c.get("is_own")), "source_url": c.get("source_url")} for c in self.run.db_cards]
            counts = {t: 0 for t in self.run.allowed_tags}
            for c in cards:
                if c["is_own"]:
                    continue                       # 자사 카드는 경쟁 집계(혼잡·공백)에서 뺀다
                for t in c["tags"]:
                    counts[t] = counts.get(t, 0) + 1
            if self.run.own_issuer:
                d["payload"]["own_issuer"] = self.run.own_issuer
                d["conversation"]["own_cards"] = [c["name"] for c in cards if c["is_own"]]
            d["payload"].update(allowed_tags=self.run.allowed_tags, competitor_db={"as_of": self.run.db_as_of, "cards": cards}, tag_counts=counts,
                                target_segment=self.run.scope["target_segment"],
                                topic=f"{self.run.scope['target_segment']} 특화 신용카드 기획을 위한 혼잡·공백 혜택과 최근접 카드")
        return d

    def consumer(self):
        d = self.head("04-consumer", "consumer", "타깃 소비자의 니즈 순위와 꼭 필요한 것, 포기할 수 있는 것을 정리해줘.", "orchestrated")
        d["payload"]["trend_signals"] = [{k: s[k] for k in ("id", "title", "impl", "topic")} for s in self.out("02-trend")["result"]["signals"]]
        store = self.run.evidence
        if self.v2:
            d["payload"]["segment"] = self.seg_obj()
            d["payload"]["need_labels"] = self.run.scenario_data["need_labels"]
        if store and self.v2:
            d["payload"].update(pack_mode=True, docs=store.docs(
                lambda it: (it.get("topic") or "") in ("criteria", "motive", "barrier", "satisfaction", "churn", "app_usage", "segment_diff", "usage_stat", "payment", "card_usage")
                and it.get("relevance") in ("direct", "indirect"), k_sources=24, facts_per_source=6))
        return d

    def trend_evidence(self, topics: list[str]):
        d = self.head("02-trend-evidence", "trend", "디자인·마케팅이 요청한 주제의 근거를 기록 우선으로 찾아줘.", "orchestrated")
        d["payload"]["purpose"] = "evidence_pack"
        d["payload"]["research_topics"] = topics
        if self.v2 and self.run.evidence:     # 근거 팩 모드
            d["payload"]["pack_mode"] = True
            d["payload"]["docs"] = self.run.evidence.docs(lambda it: it.get("relevance") in ("direct", "indirect"), k_sources=12, facts_per_source=4)
        d["payload"]["known_doc_ids"] = sorted({x["id"] for st in ("02-trend", "03-competitor", "04-consumer") for x in self.out(st).get("sources", [])})
        return d

    def whitespace(self, cells_top: list[dict], excluded: list[dict]):
        d = self.head("05-whitespace", "whitespace", "목표를 지킬 수 있는 시장 기회 셀을 순위로 골라줘.")
        if self.v2:
            d["payload"]["segments"] = [{"id": x["id"], "name": x["name"]} for x in self.run.scenario_data["segments"]]
            d["payload"]["need_labels"] = self.run.scenario_data["need_labels"]
            d["payload"]["target_segment_id"] = self.run.scope["target_segment_id"]
            if self.run.scenario_data.get("pm_directions"):
                d["payload"]["pm_directions"] = self.run.scenario_data["pm_directions"]
        rl, tr, cp, cs = (self.out(s)["result"] for s in ("01-research-lead", "02-trend", "03-competitor", "04-consumer"))
        p = d["payload"]
        p["target_adopt"] = self.run.scope["target_adopt"]
        p["research"] = {"trend": [{k: s[k] for k in ("id", "title", "impl", "topic", "strength", "reliability")} for s in tr["signals"]],
                         "competitor": {k: cp[k] for k in ("crowded", "empty", "nearest")},
                         "consumer": {k: cs[k] for k in ("top_needs", "must_have", "can_give_up", "evidence_signal_ids")},
                         "lead": {k: rl[k] for k in ("headline", "key_findings", "conflicts")}}
        store = self.run.evidence
        if store:
            ev, seen = [], set()
            for c in cells_top:
                got = store.slice(need=c["need"], mechanisms=c.get("mechanisms", []), domain=c.get("domain"), k=5, per_kind=2)
                c["evidence_refs"] = [e["id"] for e in got]
                for e in got:
                    if e["id"] not in seen:
                        seen.add(e["id"])
                        ev.append(e)
            p["evidence"] = ev[:60]
        p["cells_top"] = cells_top if any("id" in c for c in cells_top) else [{k: c[k] for k in ("seg", "need", "score", "rank", "ceiling")} for c in cells_top]
        p["excluded_cells"] = excluded
        return d

    def concept(self, pick: dict, feedback: dict | None):
        d = self.head("06-concept", "concept", f"선택한 기회({pick['seg']} × {pick['need']})로 카드 컨셉 3안을 만들어줘.")
        cp, cs, tr = (self.out(s)["result"] for s in ("03-competitor", "04-consumer", "02-trend"))
        p = d["payload"]
        p["pick"] = pick
        if self.v2:
            p["segment_pack"] = dict(p["segment_pack"], allowed_tags=dict(self.run.allowed_tags), segment=self.seg_obj(),
                                     constraints=dict(p["segment_pack"]["constraints"], links_allowed=["sec", "ins", "bank"] if self.run.scope.get("allow_invest") else []))
            area = next((a for a in self.run.areas if a["id"] == pick.get("area_id")), None)
            if area and area.get("idea"):
                p["pick"] = dict(pick, idea=area["idea"])
        store = self.run.evidence
        if store:
            from .opportunity import DOMAIN_TAGS
            mechs, dom = pick.get("mechanisms", []), pick.get("domain")
            ev = store.slice(need=pick["need"], mechanisms=mechs, domain=dom, k=12, per_kind=4)
            idea = p["pick"].get("idea")
            if idea:     # 아이디어가 인용한 근거를 먼저 넣고(실재하는 것만), 니즈로 고른 것으로 채운다
                have = {e["id"] for e in ev}
                cited = [store.compact(store.items[i]) for i in (x[3:] if x.startswith("ev:") else x for x in idea.get("evidence_ids", [])) if i in store.items]
                ev = [e for e in cited if e["id"] not in have] + ev
                ev = ev[:18]
            p["pick"] = dict(p["pick"], evidence_refs=[e["id"] for e in ev])
            p["evidence"] = ev
            refs = store.nearest_cards(list(mechs) + DOMAIN_TAGS.get(dom, [])[:1], k=4, own=False)     # 경쟁 카드만
            if idea:     # 아이디어가 가장 비슷하다고 대조한 실제 카드를 먼저
                named = {n["card"] for n in idea.get("nearest_cards", [])}
                by_name = [c for c in store.nearest_cards([t for c in store.cards if c["name"] in named for t in c["tags"]], k=60, own=False) if c["name"] in named]
                refs = (by_name + [r for r in refs if r["name"] not in named])[:6]
            p["competitor_refs"] = refs
            if self.run.own_issuer:      # 자사 카드는 경쟁이 아니라 비교 대상: 같은 영역에서 가장 가까운 자사 카드(잠식 점검용)
                p["own_refs"] = store.nearest_cards(list(mechs) + DOMAIN_TAGS.get(dom, [])[:1], k=3, own=True)
            p["invest_rules"] = [{"id": e["id"], "rule": e["text"], "status": "근거 팩 기준", "as_of": e.get("published")}
                                 for e in store.slice(need=pick["need"], mechanisms=mechs, domain=dom, k=6, kinds={"constraint"})] \
                if self.run.scope.get("allow_invest") else []
        p["comp_empty"], p["comp_crowded"] = cp["empty"], cp["crowded"]
        p["consumer"] = {k: cs[k] for k in ("top_needs", "must_have", "can_give_up")}
        p["trend_refs"] = [{k: s[k] for k in ("id", "title", "impl")} for s in tr["signals"]]
        p["feedback"] = feedback
        return d

    def validation(self, winner: dict, twin: dict):
        d = self.head("07-validation", "validation", f"{winner['card']['working_title']}가 타깃에게 먹힐지 가상 고객으로 보고, 유형별 반응을 알려줘.")
        p = d["payload"]
        p["card"], p["metrics"], p["twin"], p["target_adopt"] = winner["card"], winner["metrics"], twin, twin["target_adopt"]
        return d

    def guardrail(self, winner: dict, twin: dict):
        d = self.head("08-guardrail", "guardrail", f"{winner['card']['working_title']}를 재무와 준법 관점에서 점검해줘. 고칠 것과 법무에 확인받을 것을 나눠서.")
        m, p = winner["metrics"], d["payload"]
        p["card"] = winner["card"]
        p["metrics"] = {k: m[k] for k in ("name", "profit", "novelty", "sim", "nearest", "adopt", "adopterProfit", "cherry", "appliedCx", "topReject") if k in m}
        p["twin"] = {k: twin[k] for k in ("target_adopt", "by_type", "adopter_profit", "static_profit", "scenarios") if k in twin}
        cherry = twin["by_type"].get("혜택 사냥꾼(체리피커)") or twin["by_type"].get("체리피커")
        p["precheck_flags"] = ([{"check_id": "G6", "flag": f"체리피커가 채택자의 {cherry['share_of_adopters']}로 20% 이상이면서 손익 {cherry['profit']}로 3 미만"}]
                               if cherry and cherry["share_of_adopters"] >= 0.2 and cherry["profit"] < 3 else [])
        return d

    def design_marketing(self, winner: dict, twin: dict):
        card = winner["card"]
        va, gr = self.out("07-validation")["result"], self.out("08-guardrail")["result"]
        d = self.head("09-design-marketing", "design_marketing", "확정된 카드 브리프로 이름 후보, 마케팅 방향, 카드 디자인 시안 3개, 영상 스토리보드(릴스·유튜브·홍보)를 만들어줘.")
        p = d["payload"]
        p["brief"] = {"text": f"{self.run.scope['target_segment']}를 위한 신용카드 '{card['working_title']}'의 마케팅 방향, 카드 디자인 시안, 영상 스토리보드를 만들어 주세요. {card['one_liner']}",
                      "card_type": "credit", "target": self.run.scope["target_segment"], "card_summary": card["one_liner"],
                      "special_point": card["special_point"], "mechanics": card["mechanics"], "benefits": self.benefits(card),
                      "working_title": card["working_title"]}
        if self.v2:
            p["existing_card_names"] = [c["name"] for c in self.run.db_cards]
            p["trend_signals"] = [{k: x[k] for k in ("id", "title", "impl", "reliability", "source_ids") if k in x} for x in self.out("02-trend")["result"]["signals"]]
            if self.run.evidence:
                docs = self.run.evidence.docs(lambda it: it.get("relevance") == "direct" and not it.get("stale"), k_sources=12, facts_per_source=4)
                # 09 는 출처 id 를 S<번호>로 받는다. 근거 팩의 출처 id(IVS19 등)는 순번으로 바꾸고 원래 id 는 title 앞에 남기지 않는다(원본은 근거 팩 sources.json)
                p["research_pack"] = [{"id": f"S{i + 1}", "title": x["title"], "url": x["url"], "published": x["published"], "reliability": x["reliability"], "facts": x["facts"]}
                                      for i, x in enumerate(docs)]
        p["guard_open_items"] = [{"id": c["id"], "item": c["item"], "status": c["status"], **({"suggestion": c["suggestion"]} if c.get("suggestion") else {})}
                                 for c in gr["checks"] if c["status"] in ("fix", "needs_human")]
        p["required_disclosures"] = gr.get("required_disclosures", [])
        p["twin_facts"] = {k: twin[k] for k in ("target_adopt", "by_type", "scenarios")}
        p["voices_summary"] = va["summary"]
        return d

    def benefits(self, card: dict) -> list[dict]:
        """rates·한도·실적 조건을 보드용 혜택 목록으로 변환(코드). 문자열 길이 상한은 09 in.schema 를 따른다."""
        cats = self.run.scenario_data.get("categories", {})
        out = []
        for c, r in sorted(card["rates"].items(), key=lambda kv: -kv[1])[:6]:
            out.append({"category": cats.get(c, c)[:16], "headline": f"{r * 100:g}% 캐시백"[:24],
                        "condition": f"월 한도 {card.get('capPerCat', 0) * 10000:,.0f}원 · 전월실적 {card.get('minPerf', 0)}만원 이상"[:60],
                        "source": "winner.card.rates"})
        return out

    def plan_doc(self):
        """10 기획서 입력. allowed_urls, allowed_numbers, decision_log 는 코드가 만든다."""
        run, o = self.run, self.out
        ev, tw = run.load("06-concept/eval.json"), run.load("07-validation/twin.json")
        first = ev       # 재작업 전에 승자가 있었던 가장 이른 평가(없으면 최종 평가). 첫 평가에 승자가 없었던 경우(통과 0건 → 재작업)도 있다
        k = 1
        while run.load_opt(f"06-concept/eval.attempt{k}.json") is not None:
            prev = run.load_opt(f"06-concept/eval.attempt{k}.json")
            if prev.get("winner"):
                first = prev
                break
            k += 1
        win = ev["winner"]
        tpl = self.tpl("10-plan-doc")["payload"]
        if self.v2:   # v1 템플릿의 필요 데이터 문장에는 v1 최종 지표가 문자열로 박혀 있다 → 이번 최종 지표로 다시 만든다
            m = win["metrics"]
            seg = self.run.scope["target_segment"]
            tpl = dict(tpl, needs_client_data=[
                {"item": "자사 포트폴리오 분석(카니발라이제이션)", "purpose": "기존 카드 라인업과 이 카드의 잠식·시너지를 계산한다. 필요한 입력: 기존 카드별 타깃·혜택·연회비·회원수, 해당 연령 고객의 보유 카드와 월 이용액 분포.",
                 "fallback": f"공개 시판 카드 {len(self.run.db_cards)}종 대비 새로움 {m['novelty']}, 최근접 카드({m['nearest']})와의 유사도 {m['sim']}"},
                {"item": "BEP(손익분기점)", "purpose": "고정비(개발·마케팅·심사·인건비), 발급 목표, 고객 획득 비용, 해지율, 충당금률을 받아야 계산할 수 있다. 월 단위 BEP 시점은 쓰지 않고 계산식과 필요한 입력만 쓴다.",
                 "fallback": f"가상 고객 시뮬레이션의 정적 손익 {m['profit']}와 채택 고객 기준 손익 {m['adopterProfit']}"},
                {"item": "수익 모델", "purpose": "가맹점 수수료 수익, 예상 취급고, 할부·리볼빙 전환율은 고객사 수치가 필요하다.", "fallback": "시뮬레이션 모형의 수익률 가정(PM 가정치)"},
                {"item": f"{seg} 세그먼트 수치", "purpose": "월 소비, 니즈 가중치, 복잡도 허용도는 PM 가정치다. 해당 연령 회원의 카테고리별 이용액 집계로 바꿔야 한다.", "fallback": "PM 가정치(scenario.json)"}])
        if self.v2:   # v1 템플릿의 R&R 은 v1 컨셉에 맞춘 문장이라 컨셉에 묶이지 않는 일반 R&R 로 바꾼다
            tpl = dict(tpl, rr_teams=["마케팅팀: 캠페인 기획, 매체 전략, 홍보 영상 제작 확정", "디자인팀: 카드 플레이트와 앱 UI 제작, 후보 3안 중 확정",
                                      "IT/데이터팀: 컨셉 확정 뒤 앱·데이터 구축 범위 산정(결제 내역 활용 동의, 알림, 실적 판정 로직 등)",
                                      "리스크관리팀: 수익성과 리스크 재검증, 체리피커·악용 경로 검증", "법무·준법팀: 부가서비스 변경·유지 의무, 광고 문구 심의, 개인정보 동의"])
        ws, rl, tr, cp, cs = (o(s)["result"] for s in ("05-whitespace", "01-research-lead", "02-trend", "03-competitor", "04-consumer"))
        te = o("02-trend-evidence")["result"]["signals"] if "02-trend-evidence" in run.outputs else []
        va, gr, dm = (o(s)["result"] for s in ("07-validation", "08-guardrail", "09-design-marketing"))
        alt = []
        for r in ev["eval"]:
            if r["i"] == win["metrics"]["i"]:
                continue
            why = ("통과 기준 미달: " + ", ".join(r["fails"])) if not r["pass"] else f"통과했으나 종합 점수 {r['score']}로 승자({win['metrics']['score']})보다 낮음"
            alt.append({"working_title": r["name"], "reason_dropped": why, "metrics": {k: r[k] for k in ("adopt", "profit", "novelty", "sim", "adopterProfit", "cherry")}})
        if first is not ev and first["winner"]["metrics"]["name"] != win["metrics"]["name"]:    # 같은 안을 고친 것이면 대안이 아니다
            fm = first["winner"]["metrics"]
            alt.append({"working_title": fm["name"], "reason_dropped": "1차 승자였으나 가드레일 fix로 재작업되어 현재 안이 되었다",
                        "metrics": {k: fm[k] for k in ("adopt", "profit", "novelty", "sim", "adopterProfit", "cherry")}})
        research = {"headline": rl["headline"], "key_findings": rl["key_findings"], "conflicts": rl["conflicts"], "uncertainties": rl.get("uncertainties", []),
                    "signals": [{k: s[k] for k in ("id", "title", "impl", "reliability", "stale", "research_topic") if k in s} for s in tr["signals"] + te],
                    "competitor": {k: cp[k] for k in ("crowded", "empty", "nearest")},
                    "consumer": {k: cs[k] for k in ("top_needs", "must_have", "can_give_up")}}
        design = {"naming": dm["naming"],
                  "strategy": {k: dm["strategy"].get(k) for k in ("positioning", "pillars", "channels", "phases", "kpis", "risks") if k in dm["strategy"]},
                  "boards": {"concept": dm["boards"].get("concept"), "variants": [{k: v.get(k) for k in ("code", "name", "story") if k in v} for v in dm["boards"].get("variants", [])]},
                  "storyboards": {k: {"duration_s": v.get("duration_s"), "scenes": [{kk: sc.get(kk) for kk in ("t", "visual", "caption", "voiceover", "duration_s") if kk in sc} for sc in v.get("scenes", [])]}
                                  for k, v in dm["storyboards"].items()},
                  "segment_plays": dm.get("segment_plays"), "compliance": dm.get("compliance"), "needs_research": dm.get("needs_research")}
        decision_log = [{"step": e["event"], "event": e["detail"], "effect": e.get("agent") or "-"} for e in self.run.bus.events
                        if e["event"] in {"gate", "human_decision", "rework", "code_fix", "code"}]
        stages = ["01-research-lead", "02-trend", "02-trend-evidence", "03-competitor", "04-consumer", "05-whitespace", "06-concept", "07-validation", "08-guardrail", "09-design-marketing"]
        urls = sorted({s["url"] for st in stages if st in run.outputs for s in run.outputs[st].get("sources", [])
                       if s.get("url") and not s["url"].startswith("https://card-studio.invalid")})
        chosen = run.pick
        core = {"research": research, "opportunity": {"picks": ws["picks"], "chosen": chosen}, "final_card": self.label_card(win["card"]),
                "final_metrics": win["metrics"], "alternatives": alt, "twin": va["twin"], "voices": va["voices"], "guardrail": gr, "design_marketing": design}
        nums: set = set()
        for part in (core, tpl["needs_client_data"], tpl["rr_teams"], decision_log):
            self._nums(part, nums)
        d = self.head("10-plan-doc", "plan_doc", "지금까지 나온 결과를 모아서 7개 섹션 틀로 기획서를 써줘. 모르는 숫자는 만들지 말고, 고객 데이터가 필요한 건 뭐가 필요한지 적어줘.")
        d["payload"] = dict(core, template=tpl["template"], style=tpl["style"], needs_client_data=tpl["needs_client_data"], rr_teams=tpl["rr_teams"],
                            schedule_note=tpl["schedule_note"], allowed_urls=urls, allowed_numbers=sorted(nums), decision_log=decision_log)
        return d

    def label_card(self, card: dict) -> dict:
        """내부 필드명(segId, capPerCat…)을 사람이 읽는 라벨로 바꾼다. 라벨표는 시나리오 팩."""
        sc = self.run.scenario_data
        labels = {"segId": "타깃 세그먼트", "need": "니즈", "tags": "혜택 유형", "rates": "영역별 캐시백률", "capPerCat": "영역별 월 한도(만원)",
                  "fee": "연회비(만원)", "minPerf": "전월 이용실적 기준(만원)", "cx": "복잡도(자기보고)", "links": "그룹사 연계"}
        tags = self.run.allowed_tags if self.v2 else self.tpl("03-competitor")["payload"]["allowed_tags"]
        out = {}
        for k, v in card.items():
            if k == "tags":
                v = [tags.get(t, t) for t in v]
            if k == "rates":
                v = {sc.get("categories", {}).get(c, c): r for c, r in v.items()}
            out[labels.get(k, k)] = v
        return out

    @staticmethod
    def _nums(o, acc: set):
        if isinstance(o, bool):
            return
        if isinstance(o, (int, float)):
            acc.add(str(o))
            if 0 < abs(o) <= 1:
                acc.update({f"{o * 100:.1f}%", f"{o * 100:.0f}%"})
        elif isinstance(o, str):
            acc.update(re.findall(r"\d+(?:\.\d+)?%", o))
            acc.update(re.findall(r"\d+(?:\.\d+)?", o))
        elif isinstance(o, dict):
            for v in o.values():
                Builder._nums(v, acc)
        elif isinstance(o, list):
            for v in o:
                Builder._nums(v, acc)
