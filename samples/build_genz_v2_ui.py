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
    for e, o in zip(evalj, opts):
        cands.append({"name": e["name"], "hook": o["one_liner"], "profit": e["profit"], "sim": e["sim"], "adopt": e["adopt"],
                      "adopterProfit": e["adopterProfit"], "appliedCx": e["appliedCx"], "pass": e["pass"]})
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
    sb = []
    for sc in dm["storyboards"]["reels"]["scenes"]:
        words = " ".join(w for c in sc.get("captions", []) for w in c["words"])
        sb.append({"visual": f'릴스 {sc["id"]} · {sc.get("variant", "공통")} · {sc["duration_s"]}초', "copy": words or "(자막 없음)"})
    sb = sb[:6]
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
                  "storyboard": sb, "needs_research": nr},
        "designs": designs, "designRec": "A", "designPrefix": "genz_v2_design_", "promo": False, "heroH": 330, "designBack": True,
        "marketing": {"core": dm["strategy"]["positioning"]["statement"],
                      "lifecycle": [{"stage": p["name"], "goal": p["goal"], "actions": p.get("actions", []), "days": f'D{p["start_day"]:+d} ~ D{p["end_day"]:+d}'} for p in dm["strategy"]["phases"]]},
    }

    DATA["doc_head"] = doc_head
    if extra:
        DATA.update({k: v for k, v in extra.items() if k not in ("ui", "_guard_final")})
        DATA["ui"] = dict(DATA.get("ui", {}), **extra.get("ui", {}))
    DATA["ui"]["trendRef"] = True        # ui/genz-trend-ref.js (Opus 정리 트렌드 참고자료)
    return DATA




def wrap(d):
    return json.dumps(d, ensure_ascii=False)


MAIN_EXTRA = {
    "summary": {
        "concept": "꾸준: 첫 12개월은 낮은 전월실적으로 연습하고, 연체 없이 기준을 채우면 13개월 차부터 전월실적 조건이 해제되는 GenZ 첫 신용카드",
        "conceptNote": "매달 실적 충족 여부로 혜택이 갈리는 구조 대신, 보유 이력(납부·이용)에 따라 조건이 졸업하는 구조. 졸업 후 연체 시 연습 구간으로 복귀",
        "short": {"target": "만 19~29세 GenZ, 카드 이용이 처음인 고객", "benefit": "연습 12개월 후 전월실적 해제", "diff": "실적 조건의 졸업 구조(경쟁 카드 40종·자사 10종 중 0종)"},
        "benefits": [["연습 구간(발급 후 12개월)", "전월 15만원 이상 시 외식·배달 1%, 편의점·마트 1.5% 할인, 영역별 월 한도 4천원"], ["미달 월", "국내 가맹점 0.5% 적립(연습 구간 한정)"], ["졸업(13개월 차~)", "12개월 연체 0회 + 9개월 이상 월 이용 금액 기준 충족 시 전월실적 조건 해제, 영역별 월 한도 유지"], ["졸업 후 연체", "연습 구간으로 복귀 (상품설명서에 사전 고지)"], ["연회비", "1만원"]],
        "target": [["연령", "만 19~29세 (신용카드 발급 가능 연령)"], ["카드 경험", "카드 이용이 처음인 고객을 주 대상으로 하되, 첫 카드 여부를 확인하는 장치는 두지 않음"], ["핵심 니즈", "단순함(PM 가정 연결) + 절약·캐시백"], ["결제 습관", "간편결제 등록, 앱 내 발급·관리 중심"]],
        "diffs": [["졸업형 실적 구조", "경쟁 카드 40종 중 perf_graduation 0종, zero_floor 1종, 실적 구간제 9종(자사 신한카드 10종 중 5종은 별도)"], ["미달 월에도 혜택 0 방지", "연습 구간 미달 월 0.5% 적립 유지"], ["규칙 사전 고지", "졸업 조건과 복귀 규칙을 상품설명서·앱에 미리 표기"], ["한계(근거 범위)", "국내 전 카드 조사가 아니며, 졸업형 선호를 보여 주는 GenZ 고객 데이터는 없음"]],
    },
    "ui": {
        "badge": "실제 LLM 호출 없음 · 근거 팩 v2 실행 기록 재생",
        "date": "근거 팩 v2 실행 기록",
        "reresearch": False,
        "researchPrompt": "GenZ 신용카드 시장 흐름과 경쟁 공백을 알려줘",
        "researchSub": "트렌드·경쟁사·소비자 조사는 미리 쌓아 둔 근거 팩(735건, 출처 261개)을 읽어 만들었습니다. 경쟁사는 시판 카드 40종 기준이고 신한카드 10종은 자사로 분리해 비교만 합니다. 근거 신뢰도가 낮은 항목은 낮음으로 표시합니다.",
        "wsSub": "먼저 발굴 파이프라인(조사 → 공백 후보 31개 → 컨셉 아이디어 32개 → 3관점 반박 검증)을 돌렸고, 코드가 12개 기회 영역(니즈 × 혜택 방식 × 영역, 검증된 아이디어 영역 포함)을 점수화했습니다. 에이전트가 상위 3개를 골랐고, 3순위는 PM 관심 방향(졸업·실적 재해석)에 맞는 아이디어 영역입니다.",
        "conceptSub": "에이전트가 서로 다른 3안을 내고 코드가 손익·유사도·복잡도·채택 의향을 계산했습니다. 첫 시도에서는 3안 모두 손익·복잡도 기준을 못 넘어 재작업했고, 2차에서 2안이 통과해 졸업 카드가 채택 의향 0.438로 선정됐습니다. 미달 월 환급안은 채택 의향 0.265로 탈락했습니다.",
        "guardSub": "1차 점검에서 문구 3건(G1·G2·G6)이 fix였고, 이름·문구 수정 뒤 G1·G2는 통과했습니다. G6(졸업 이용 금액 미정·환수 미정·시뮬레이션 미반영)과 준법·개인정보 확인(G3·G4)은 남아 기획서 리스크로 이월했습니다. 아래는 수정 전 점검 결과입니다.",
        "designNote": "시안은 모눈 낮(GRID)·투명 눈금(CLEAR)·밤 모눈(NIGHT) 3종입니다. 영상은 H5 확정 전이라 렌더하지 않고 스토리보드로 대신합니다.",
        "docNote": "고객 틀 7개 섹션 + 부록으로 작성했습니다. 아래는 앞부분이며 전체는 scenarios/genz-credit-v2/기획서_꾸준카드.md에 있습니다.",
        "human": {
            "H1": "해석한 범위: 타깃 GenZ(만 19~29세), 카드 유형 신용카드, 투자 연계는 제외(규칙만 06에 전달). 이대로 진행할까요?",
            "H2": "상위 3개 셀 중 컨셉을 만들 셀을 고릅니다. 이 실행 기록에서는 사람이 3순위(졸업·실적 재해석 아이디어)를 골랐습니다.",
            "H3": "사람 확인이 필요한 항목(준법·개인정보)을 담당 부서에 배정합니다. 진행은 계속하고 기획서 부록에 미확인으로 남깁니다.",
            "H4": "‘실적 졸업 카드’로 확정할까요? 확정하면 이름·디자인·마케팅 단계로 넘어갑니다.",
            "H5": "스토리보드 미리보기를 확인했습니다. 영상은 렌더하지 않고 스토리보드로 대체합니다.",
        },
    },
}

# 기본 경로 = H2 1순위(scenarios/genz-credit-v2-alt), 분기 = H2에서 3순위(졸업 아이디어)를 고른 경로(scenarios/genz-credit-v2)
MAIN_EXTRA["pickIdx"] = 2
MAIN_EXTRA["designRec"] = "B"
DATA_BRANCH = build(V2, MAIN_EXTRA)
DATA_V2 = None
if (ALT / "10-plan-doc" / "out.json").exists() and (ALT / "ui_extra.json").exists():
    DATA_V2 = build(ALT, json.loads((ALT / "ui_extra.json").read_text(encoding="utf-8")))
out = ""
if DATA_V2:
    out += "window.DATA_GENZ_V2=" + wrap(DATA_V2) + ";\n"
out += "window.DATA_GENZ_V2_ALT=" + wrap(DATA_BRANCH) + ";\n"
(UI / "genz-v2-data.js").write_text(out, encoding="utf-8")
print("ok", len(out), "bytes", "main" if DATA_V2 else "no-main")
