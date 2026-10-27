"""GenZ v2 실행 기록(scenarios/genz-credit-v2, -alt)을 사용자 뷰 데이터로 바꾼다.

실행: python3 samples/build_genz_v2_ui.py
출력: ui/genz-v2-data.js (window.DATA_GENZ_V2, window.DATA_GENZ_V2_ALT)
값은 기록 그대로 두고 모양만 사용자 뷰의 DATA 형식에 맞춘다. 손으로 쓴 것은 summary·ui 문구뿐이다(자사 비교표는 카드 DB와 03 결과로 계산).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "ui"
V2 = ROOT / "scenarios" / "genz-credit-v2"
ALT = ROOT / "scenarios" / "genz-credit-v2-alt"
SC = V2


def load(rel):
    d = json.loads((SC / rel).read_text(encoding="utf-8"))
    return d.get("result", d), d


uv = (UI / "user-view.html").read_text(encoding="utf-8")
i = uv.index("var DATA=") + 9
j = uv.index(";\nDATA.summary=")
base = json.loads(uv[i:j])
labels = base["labels"]
labels["seg"]["genz"] = "GenZ(만 19~29세)"
_db = json.loads((V2 / "competitor_db.json").read_text(encoding="utf-8"))
labels["tag"].update(_db["allowed_tags"])
labels["need"].update(json.loads((V2 / "scenario.json").read_text(encoding="utf-8"))["need_labels"])
_areas = {a["id"]: a for a in json.loads((V2 / "areas.json").read_text(encoding="utf-8"))}
_disc = json.loads((V2 / "evidence/summary.json").read_text(encoding="utf-8"))
_idea_rank = json.loads((V2 / "evidence/ideas_ranked.json").read_text(encoding="utf-8"))
_ev = json.loads((V2 / "evidence/evidence_index.json").read_text(encoding="utf-8"))["items"]


def build(scdir, extra=None):
    """실행 기록 폴더 하나를 사용자 뷰 DATA로 바꾼다. extra는 손으로 쓴 요약·포지셔닝·문구 덮어쓰기."""
    global SC
    SC = scdir
    trend, trend_env = load("02-trend/out.json")
    comp, _ = load("03-competitor/out.json")
    cons, _ = load("04-consumer/out.json")
    ws, _ = load("05-whitespace/out.json")
    concept, _ = load("06-concept/out.json")
    evalj = json.loads((SC / "06-concept/eval.json").read_text(encoding="utf-8"))["eval"]
    win_i = json.loads((SC / "06-concept/eval.json").read_text(encoding="utf-8"))["winner"]["metrics"]["i"]
    val, _ = load("07-validation/out.json")
    guard1, _ = load("08-guardrail/out.attempt1.json" if (SC / "08-guardrail/out.attempt1.json").exists() and not (extra or {}).get("_guard_final") else "08-guardrail/out.json")
    dm, _ = load("09-design-marketing/out.json")
    plan, _ = load("10-plan-doc/out.json")

    src = {s["id"]: s for s in trend_env.get("sources", [])}
    signals = []
    for s in trend["signals"]:
        signals.append({
            "id": s["id"], "title": s["title"], "topic": s["topic"], "strength": s["strength"],
            "reliability": s["reliability"], "impl": s["impl"],
            "sources": [{"url": src[x].get("url", ""), "title": src[x].get("title", ""), "published": src[x].get("published")}
                        for x in s.get("source_ids", []) if x in src],
        })

    opts = concept["options"]
    cands = []
    scen = json.loads((SC / "scenario.json").read_text(encoding="utf-8"))
    cats = scen["categories"]
    LEVER = {"benefit_structure": "혜택 구조", "experience": "앱 경험", "target_subsegment": "세부 타깃", "partnership": "제휴 구조",
             "price": "가격·조건", "pricing": "가격·조건", "channel": "발급·이용 채널"}
    for k, (e, o) in enumerate(zip(evalj, opts)):
        cv = o.get("cvp", {})
        cands.append({"name": e["name"], "hook": o["one_liner"], "profit": e["profit"], "sim": e["sim"], "adopt": e["adopt"],
                      "adopterProfit": e["adopterProfit"], "appliedCx": e["appliedCx"], "pass": e["pass"], "winner": k == win_i,
                      "lever": LEVER.get(o.get("lever"), o.get("lever")), "variation": o.get("variation"),
                      "target": cv.get("target"), "need": cv.get("need"), "offer": cv.get("offer"), "key_benefit": cv.get("key_benefit"),
                      "alternative": cv.get("alternative"), "differentiator": cv.get("differentiator"),
                      "rates": [[cats.get(c, c), round(r * 100, 1)] for c, r in o["rates"].items()],
                      "fee": o.get("fee"), "cap": o.get("capPerCat"), "minPerf": o.get("minPerf"), "tags": o["tags"],
                      "mechanics": o["mechanics"], "special": (o.get("special_point") or {}).get("hook"),
                      "why_unusual": (o.get("special_point") or {}).get("why_unusual")})
    win = opts[win_i]

    twin = val["twin"]
    twin_out = {
        "target_adopt": twin["target_adopt"], "static_profit": twin["static_profit"], "adopter_profit": twin["adopter_profit"],
        "behav_floor": twin["behav_floor"], "all_segments_adopt": twin["all_segments_adopt"],
        "by_type_in_target": {k: {"share_of_adopters": v["share_of_adopters"], "profit_만원": v["profit"]} for k, v in twin["by_type"].items()},
        "scenarios": twin["scenarios"],
    }

    variants = dm["boards"]["variants"]
    codes = ["A", "B", "C"]
    designs = {codes[k]: {"title": f'{v["code"]} · {v["name"]}'} for k, v in enumerate(variants)}
    PRESET = {"hero_reveal": "카드가 화면에 처음 등장한다", "hero_float": "카드가 천천히 떠올라 앞면을 보여 준다",
              "detail_closeup": "카드 소재와 디테일을 가까이 보여 준다", "flip": "카드를 뒤집어 뒷면의 이용 조건을 보여 준다",
              "fan_merge": "시안 여러 장이 펼쳐졌다가 하나로 모인다", "benefit_card": "혜택 안내 카드(조건을 같은 크기로 함께 표기)",
              "stack_lockup": "로고와 이름으로 마무리한다", "split_merge": "여러 장면이 하나로 합쳐지며 같은 카드로 이어진다",
              "heartbeat_intro": "심장박동처럼 카드가 등장하는 도입", "beat_words": "박자에 맞춰 핵심 단어가 차례로 나온다",
              "lineup_pulse": "시안 라인업이 박자에 맞춰 차례로 강조된다", "material_marquee": "카드 소재 클로즈업이 흐르듯 이어진다"}
    FOCUS = {"material": "소재", "chip": "칩", "edge": "옆면", "logo": "로고", "back": "뒷면"}
    FMT = {"reels": "릴스(세로 영상)", "youtube": "유튜브(가로 영상)", "promo": "홍보 영상(가로)"}
    storyboards = []
    for fmt in ("reels", "youtube", "promo"):
        v = dm["storyboards"][fmt]
        scs = []
        for k, sc in enumerate(v["scenes"], 1):
            note = (sc.get("params") or {}).get("note")
            words = (sc.get("params") or {}).get("words")
            vis = (note.split(". ")[0].rstrip(".") if note else PRESET.get(sc["preset"], sc["preset"]))
            if sc["preset"] == "detail_closeup":
                vis = "카드 " + FOCUS.get((sc.get("params") or {}).get("focus"), "디테일") + "을 가까이 보여 준다"
            if sc["preset"] == "beat_words" and words:
                vis = "박자에 맞춰 핵심 단어가 차례로 나온다"
            caps = [" ".join(c["words"]) for c in sc.get("captions", [])]
            if sc["preset"] == "beat_words" and words:
                caps = [" · ".join(words[:8]) + (" …" if len(words) > 8 else "")]
            t0, d = sc.get("start_s", 0), sc.get("duration_s", 0)
            scs.append({"n": k, "time": f"{t0:g}~{t0 + d:g}초", "label": (sc.get("label") or "").split(" ", 1)[-1] if sc.get("label") else "",
                        "visual": vis, "captions": caps})
        storyboards.append({"format": FMT[fmt], "duration": v["duration_s"], "aspect": v.get("aspect"), "scenes": scs})
    sb = [{"visual": f'{x["format"]} 장면 {sc["n"]}', "copy": " / ".join(sc["captions"]) or "(자막 없음)"} for x in storyboards[:1] for sc in x["scenes"]][:6]
    stg = dm["strategy"]
    strategy = {"positioning": stg["positioning"], "insight": stg["insight"], "personas": stg["personas"], "pillars": stg["pillars"],
                "channels": stg["channels"], "phases": [{"name": p["name"], "days": f'D{p["start_day"]:+d} ~ D{p["end_day"]:+d}', "goal": p["goal"], "actions": p.get("actions", [])} for p in stg["phases"]],
                "kpis": stg["kpis"], "tone": stg["tone"], "risks": stg["risks"], "next_steps": stg["next_steps"]}
    sp = scen["sim_params"]
    gz = next(x for x in scen["segments"] if x["id"] == scen["scope"]["target_segment"])
    TYPE_DESC = {"일반형": "평균적인 소비 습관으로 카드를 쓰는 고객", "체리피커": "혜택 조건을 채우는 데 소비를 맞추는 혜택 사냥꾼",
                 "충성형": "기존에 쓰던 카드를 쉽게 바꾸지 않는 고객", "휴면 위험형": "발급은 받아도 카드를 거의 쓰지 않을 위험이 있는 고객"}
    need_lbl = scen["need_labels"]
    persona_brief = {
        "segment": gz["name"], "n": sp["n_per_segment"], "digital": gz.get("digital_level"), "tolerance": gz.get("complexity_tolerance"),
        "spend": [[cats.get(c, c), v] for c, v in sorted(gz["monthly_spend"].items(), key=lambda kv: -kv[1])],
        "needs": [[need_lbl.get(n, n), w] for n, w in sorted(gz["need_weights"].items(), key=lambda kv: -kv[1])][:5],
        "types": [{"name": "혜택 사냥꾼(체리피커)" if t == "체리피커" else t, "share": sp["type_mix"][t], "desc": TYPE_DESC.get(t, ""),
                   "use": sp["card_share"][t], "inertia": sp["inertia_mean"][t]} for t in sp["type_mix"]],
        "scenarios": [["기본", "혜택·소비·새로움이 가정한 그대로인 경우"], ["경쟁사 모방", "다른 카드사가 비슷한 카드를 내서 새로움의 매력이 절반으로 줄어든 경우"],
                      ["혜택 20% 축소", "비용 때문에 혜택률을 20% 줄인 경우"], ["시장 위축", "경기 위축으로 고객의 소비가 15% 줄어든 경우"]],
        "note": gz.get("note") or ""}
    handoff = {"directions": scen.get("pm_directions", []), "constraints": scen["scope"].get("constraints", []), "target_adopt": scen["scope"]["target_adopt"]}
    palette = [p["hex"] for p in dm["boards"]["palette"]]

    md = plan["markdown"]
    parts = re.split(r"(?m)^(?=## )", md)
    doc_head = "".join(parts[:3])[:3000]

    nr = [x if isinstance(x, str) else json.dumps(x, ensure_ascii=False) for x in dm["needs_research"]]

    wtags = set(win["tags"])
    own_cards = []
    for c in _db["cards"]:
        if not c.get("is_own"):
            continue
        shared = sorted(wtags & set(c["tags"]))
        jac = len(shared) / len(wtags | set(c["tags"])) if (wtags | set(c["tags"])) else 0.0
        own_cards.append({"name": c["name"], "type": c["type"], "target": c.get("target", ""), "annual_fee": c.get("annual_fee"),
                          "tags": c["tags"], "genz_fit": c.get("genz_fit"), "genz_fit_reason": c.get("genz_fit_reason"),
                          "headline": [h["text"] for h in (c.get("headline_benefits") or [])[:2]],
                          "shared": shared, "overlap": round(jac, 2), "source_url": c.get("source_url")})
    own_cards.sort(key=lambda x: (-x["overlap"], x["name"]))
    cmp_own = comp.get("comparison_with_own_card") or {}
    DATA = {
        "request": "GenZ 신용카드 신상품 기획해줘",
        "labels": labels,
        "signals": signals,
        "comp": {"crowded": [c["tag"] for c in comp["crowded"]], "empty": [c["tag"] for c in comp["empty"]], "counts": {c["tag"]: c["count"] for c in comp["crowded"] + comp["empty"]}, "total": sum(1 for c in _db["cards"] if not c.get("is_own")), "own_total": sum(1 for c in _db["cards"] if c.get("is_own")),
                 "nearest": [{"name": n["name"], "why": n["why"]} for n in comp["nearest"]]},
        "own": {"issuer": "신한카드", "cards": own_cards, "own_card": cmp_own.get("own_card", ""), "differences": cmp_own.get("differences", []), "gaps": cmp_own.get("gaps", [])},
        "cons": {"top_needs": [{"priority": n["priority"], "need": n["need"], "evidence": n["evidence"]} for n in cons["top_needs"]],
                 "must_have": cons["must_have"], "can_give_up": cons["can_give_up"], "barriers": cons["barriers"]},
        "picks": [{"seg": p["seg"], "need": p["need"], "rationale": p["rationale"], "evidence_ids": p.get("evidence_ids", []), "risk": p.get("risk"),
                   "title": (_areas[p["area_id"]].get("idea") or {}).get("name") if p.get("area_id", "").startswith("IDEA-") else None,
                   "statement": p.get("statement"), "unmet_gap": p.get("unmet_gap"), "confidence": p.get("confidence"), "kill_criteria": p.get("kill_criteria")} for p in ws["picks"]],
        "discovery": {"evidence_items": _disc["evidence_items"], "gap_candidates": _disc["gap_candidates"], "ideas": _disc["ideas"],
                      "finalists": len(_disc["finalists"]), "new_tags": len(_disc["new_tags"]), "areas": len(_areas),
                      "top_ideas": [{"id": r["id"], "sum": r["sum"], "grades": r["grades"]} for r in _idea_rank["ranking"][:6]]},
        "candidates": cands,
        "winner": {"card": {"name": win["working_title"], "hook": win["one_liner"], "mechanics": win["mechanics"], "tags": win["tags"]}},
        "twin": twin_out,
        "voices": val["voices"],
        "guard": {"checks": guard1["checks"], "name_mechanism_consistent": guard1["name_mechanism_consistent"], "overall": guard1["overall"]},
        "brand": {"names": [{"name": c["name"], "rationale": c["rationale"]} for c in dm["naming"]["candidates"]],
                  "recommended": dm["naming"]["recommended"],
                  "design": {"motif": dm["boards"]["concept"]["statement"], "palette": palette, "tone": dm["strategy"]["tone"]["summary"]},
                  "storyboard": sb, "storyboards": storyboards, "needs_research": nr},
        "designs": designs, "designRec": "A", "designPrefix": "genz_v2_design_", "promo": False, "heroH": 330, "designBack": True,
        "persona_brief": persona_brief, "handoff": handoff, "strategy": strategy,
        "marketing": {"core": dm["strategy"]["positioning"]["statement"],
                      "lifecycle": [{"stage": p["name"], "goal": p["goal"], "actions": p.get("actions", []), "days": f'D{p["start_day"]:+d} ~ D{p["end_day"]:+d}'} for p in dm["strategy"]["phases"]]},
    }

    DATA["doc_head"] = doc_head
    # 기회 영역 12개 전체(설명 파일이 있으면 합친다)
    expf = ROOT / "scenarios/genz-evidence/opportunity_explain.json"
    expl = json.loads(expf.read_text(encoding="utf-8")) if expf.exists() else None
    ex_by = {a["id"]: a for a in (expl or {}).get("areas", [])}
    chosen = {p.get("area_id"): k for k, p in enumerate(ws["picks"])}
    DATA["areas"] = {"intro": (expl or {}).get("intro"), "picks_note": (expl or {}).get("picks_note"),
                     "list": [{"id": a["id"], "rank": a["rank"], "score_pct": round(a["score"] * 100), "need": a["need"], "mechanisms": a["mechanisms"], "domain": a.get("domain_label"),
                               "chosen": chosen.get(a["id"]), **{k: ex_by.get(a["id"], {}).get(k) for k in ("label", "need_ko", "approach_ko", "connects", "evidence", "risk", "status", "reason")}}
                              for a in sorted(_areas.values(), key=lambda x: x["rank"])]}
    for k, p in enumerate(ws["picks"]):
        DATA["picks"][k]["area_id"] = p.get("area_id")
        ea = ex_by.get(p.get("area_id"))
        if ea:
            DATA["picks"][k].update({"label": ea.get("label"), "connects": ea.get("connects"), "reason": ea.get("reason"), "approach_ko": ea.get("approach_ko"), "evidence_ko": ea.get("evidence"), "risk_ko": ea.get("risk")})
    # 포지셔닝 맵(가로: 전월실적 부담, 세로: 혜택 구조의 희소성) — 카드 DB 값으로 계산
    allc = _db["cards"]
    comp_cnt = {}
    for c in allc:
        if not c.get("is_own"):
            for t in c["tags"]:
                comp_cnt[t] = comp_cnt.get(t, 0) + 1
    def rare(c):
        return sum(1 for t in c["tags"] if comp_cnt.get(t, 0) <= 5)
    pts = []
    for c in allc:
        mp = c.get("min_prev_month_spend_won")
        if mp is None:
            continue
        pts.append([c["name"], c["issuer"], 1 if c.get("is_own") else 0, round(min(mp / 10000, 100)), rare(c)])
    nw = {"name": win["working_title"], "x": float(win.get("minPerf", 0)), "y": rare({"tags": win["tags"]})}
    DATA["posmap"] = {"cards": pts, "new": nw, "nearest": [n["name"] for n in comp["nearest"]], "n_comp": sum(1 for c in allc if not c.get("is_own")), "n_own": sum(1 for c in allc if c.get("is_own"))}
    # 자사 vs 경쟁사 비교(카드사별)
    iss = {}
    for c in allc:
        key = "신한카드(자사)" if c.get("is_own") else c["issuer"]
        g = iss.setdefault(key, {"issuer": key, "own": bool(c.get("is_own")), "n": 0, "youth": 0, "tags": {}, "mins": []})
        g["n"] += 1
        g["youth"] += 1 if c.get("genz_fit") in ("high", "mid") else 0
        for t in c["tags"]:
            g["tags"][t] = g["tags"].get(t, 0) + 1
        if c.get("min_prev_month_spend_won") is not None:
            g["mins"].append(c["min_prev_month_spend_won"] / 10000)
    core = {"auto_best", "select_pack", "miss_refund", "perf_graduation", "zero_floor", "anti_cap", "time_slot", "subscription_ledger", "challenge", "life_event", "social", "group_pooling", "ai_personalize"}
    rows = []
    for key, g in iss.items():
        top = sorted(((t, n) for t, n in g["tags"].items() if t not in ("reward_discount", "reward_point", "reward_cashback", "check_card")), key=lambda x: -x[1])[:3]
        uniq = sorted(((t, n) for t, n in g["tags"].items() if t in core), key=lambda x: -x[1])[:3]
        rows.append({"issuer": key, "own": g["own"], "n": g["n"], "youth": g["youth"], "avg_min": round(sum(g["mins"]) / len(g["mins"])) if g["mins"] else None,
                     "top": [t for t, _ in top], "rare": [[t, n] for t, n in uniq]})
    rows.sort(key=lambda r: (not r["own"], -r["n"]))
    keytags = [t for t in win["tags"] if t not in ("reward_cashback", "reward_discount", "reward_point")][:3]
    have = {}
    for c in allc:
        key = "신한카드(자사)" if c.get("is_own") else c["issuer"]
        for t in keytags:
            if t in c["tags"]:
                have.setdefault(t, {}).setdefault(key, 0)
                have[t][key] += 1
    DATA["compare"] = {"rows": rows[:8], "keytags": keytags, "have": have}
    # 마케팅 단계 요청 보완 조사(트렌드 분석)
    evp = scdir / "02-trend-evidence" / "out.json"
    if evp.exists():
        ev = json.loads(evp.read_text(encoding="utf-8"))["result"]
        inp = scdir / "02-trend-evidence" / "in.json"
        topics = json.loads(inp.read_text(encoding="utf-8"))["payload"].get("research_topics", []) if inp.exists() else []
        DATA["reresearch"] = {"topics": topics, "signals": [{"title": x["title"], "impl": x.get("impl"), "strength": x.get("strength")} for x in ev.get("signals", [])],
                              "unresolved": ev.get("unresolved", []), "regulatory": [r.get("title") or r.get("summary") or str(r) for r in ev.get("regulatory_changes", [])][:4]}
    if extra:
        DATA.update({k: v for k, v in extra.items() if k not in ("ui", "_guard_final")})
        DATA["ui"] = dict(DATA.get("ui", {}), **extra.get("ui", {}))
    fp = SC / "followups.json"          # 중간 확인 질문 2회와 준비 답변(Opus 사전 작성)
    if fp.exists():
        DATA["followups"] = json.loads(fp.read_text(encoding="utf-8"))
    DATA["ui"]["researchSub"] = "트렌드 분석·경쟁사 분석·소비자 분석을 미리 모아 둔 자료로 정리했습니다. 경쟁 카드 130종을 살펴보고 신한카드 33종은 자사로 분리해 비교만 했습니다. 출처 신뢰도가 낮은 항목은 ‘낮음’으로 표시합니다."
    for key, fp2 in (("sum2", SC / "ui_summary.json"), ("sumres", ROOT / "scenarios/genz-evidence/ui_summary_research.json"),
                     ("keywords", ROOT / "scenarios/genz-evidence/trend_reference/consumer_keywords.json")):
        if fp2.exists():        # 화면 요약(bullet)과 소비 트렌드 키워드: 서브에이전트가 사전 작성
            DATA[key] = json.loads(fp2.read_text(encoding="utf-8"))
    DATA["ui"]["trendRef"] = True        # ui/genz-trend-ref.js (Opus 정리 트렌드 참고자료)
    return DATA




def wrap(d):
    return json.dumps(d, ensure_ascii=False)


# 세 경로: 기본 = H2 1순위(scenarios/genz-credit-v2-alt, window.DATA_GENZ_V2), 2순위(genz-credit-v2-p2, DATA_GENZ_V2_P2),
#          3순위 = 졸업 아이디어(genz-credit-v2, DATA_GENZ_V2_ALT)
P2 = ROOT / "scenarios" / "genz-credit-v2-p2"
PATHS = [("DATA_GENZ_V2", ALT, None, "alt"), ("DATA_GENZ_V2_P2", P2, None, "p2"), ("DATA_GENZ_V2_ALT", V2, None, "p3")]
out, variants = "", {}
for var, d, extra, key in PATHS:
    if extra is None:
        up = d / "ui_extra.json"
        if not ((d / "10-plan-doc" / "out.json").exists() and up.exists()):
            continue
        extra = json.loads(up.read_text(encoding="utf-8"))
    data = build(d, extra)
    data["variantsKey"] = key
    vp = d / "variants.json"
    if vp.exists():
        vv = json.loads(vp.read_text(encoding="utf-8"))
        for m in vv["grid"].values():      # 화면에서 쓰지 않는 유형별 값은 뺀다(파일 크기)
            m.pop("byType", None)
        variants[key] = vv
    out += "window.%s=" % var + wrap(data) + ";\n"
# 최종 확인에서 ‘다른 CVP 후보로 변경’을 골랐을 때 재생하는 실제 실행 기록(후보 0·2). 키는 부모 경로.
CVP = {}
cvp_js = "window.CVPALT=window.CVPALT||{};\n"
for pkey, pdir, pvar in (("alt", ALT, "DATA_GENZ_V2"), ("p2", P2, "DATA_GENZ_V2_P2"), ("p3", V2, "DATA_GENZ_V2_ALT")):
    CVP[pkey] = {}
    for k in (0, 2):
        d = ROOT / "scenarios" / f"{pdir.name}--c{k}"
        up = d / "ui_extra.json"
        if not ((d / "10-plan-doc" / "out.json").exists() and up.exists()):
            continue
        data = build(d, json.loads(up.read_text(encoding="utf-8")))
        if "followups" not in data and (pdir / "followups.json").exists():
            data["followups"] = json.loads((pdir / "followups.json").read_text(encoding="utf-8"))
        data["variantsKey"] = f"{pkey}-c{k}"
        data["switchKey"] = pkey
        vp = d / "variants.json"
        if vp.exists():
            vv = json.loads(vp.read_text(encoding="utf-8"))
            for m in vv["grid"].values():
                m.pop("byType", None)
            variants[data["variantsKey"]] = vv
        CVP[pkey][k] = data
    if CVP[pkey]:
        cvp_js += "window.CVPALT[%s]={%s};\n" % (json.dumps(pkey), ",".join('"%d":%s' % (k, wrap(v)) for k, v in CVP[pkey].items()))
        cvp_js += "window.CVPALT[%s][1]=window.%s;\n" % (json.dumps(pkey), pvar)
import sys
sys.path.insert(0, str(Path(__file__).parent))
from mark_script import mark
(UI / "genz-v2-data.js").write_text(mark(out), encoding="utf-8")
(UI / "genz-v2-cvp.js").write_text(mark(cvp_js), encoding="utf-8")
(UI / "genz-variants.js").write_text("window.VARIANTS=" + json.dumps(variants, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
print("ok", len(out), "bytes", [k for _, _, _, k in PATHS], "variants", list(variants))
