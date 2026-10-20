"""GenZ 특화 신용카드 실행 기록(scenarios/genz-credit/)을 사용자 뷰용 데이터로 바꾼다.

실행: python3 samples/build_genz_ui.py
출력: ui/genz-data.js (window.DATA_GENZ), ui/assets/genz_design_A.svg ~ C.svg
값은 기록 그대로 두고 모양만 사용자 뷰의 DATA 형식에 맞춘다. 지어낸 값은 없다.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SC = ROOT / "scenarios" / "genz-credit"
UI = ROOT / "ui"


def load(rel):
    d = json.loads((SC / rel).read_text(encoding="utf-8"))
    return d.get("result", d), d


# 라벨은 2030 케이스와 같은 것을 쓰고 GenZ 세그먼트만 더한다
uv = (UI / "user-view.html").read_text(encoding="utf-8")
i = uv.index("var DATA=") + 9
j = uv.index(";\nDATA.summary=")
base = json.loads(uv[i:j])
labels = base["labels"]
labels["seg"]["genz"] = "GenZ(만 19~29세)"

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

    DATA = {
        "request": "GenZ 특화 신용카드 만들어줘",
        "labels": labels,
        "signals": signals,
        "comp": {"crowded": [c["tag"] for c in comp["crowded"]], "empty": [c["tag"] for c in comp["empty"]], "counts": {c["tag"]: c["count"] for c in comp["crowded"] + comp["empty"]}, "total": 34,
                 "nearest": [{"name": n["name"], "why": n["why"]} for n in comp["nearest"]]},
        "cons": {"top_needs": [{"priority": n["priority"], "need": n["need"], "evidence": n["evidence"]} for n in cons["top_needs"]],
                 "must_have": cons["must_have"], "can_give_up": cons["can_give_up"], "barriers": cons["barriers"]},
        "picks": [{"seg": p["seg"], "need": p["need"], "rationale": p["rationale"], "evidence_ids": p.get("evidence_ids", []), "risk": p.get("risk")} for p in ws["picks"]],
        "candidates": cands,
        "winner": {"card": {"name": win["working_title"], "hook": win["one_liner"], "mechanics": win["mechanics"], "tags": win["tags"]}},
        "twin": twin_out,
        "voices": val["voices"],
        "guard": {"checks": guard1["checks"], "name_mechanism_consistent": guard1["name_mechanism_consistent"], "overall": guard1["overall"]},
        "brand": {"names": [{"name": c["name"], "rationale": c["rationale"]} for c in dm["naming"]["candidates"]],
                  "recommended": dm["naming"]["recommended"],
                  "design": {"motif": dm["boards"]["concept"]["statement"], "palette": palette, "tone": dm["strategy"]["tone"]["summary"]},
                  "storyboard": sb, "needs_research": nr},
        "designs": designs, "designRec": "A", "designPrefix": "genz_design_", "promo": False, "heroH": 330, "designBack": True,
        "marketing": {"core": dm["strategy"]["positioning"]["statement"],
                      "lifecycle": [{"stage": p["name"], "goal": p["goal"], "actions": p.get("actions", []), "days": f'D{p["start_day"]:+d} ~ D{p["end_day"]:+d}'} for p in dm["strategy"]["phases"]]},
        "summary": {
            "concept": "세칸: 직전 3개월 이용액 합계가 가장 큰 영역에 캐시백이 자동 배정되는 GenZ 특화 신용카드",
            "conceptNote": "외식·배달, 온라인쇼핑, 구독·디지털 3개 영역 중 1위 영역을 규칙대로 판정, 고객의 영역 선택 불필요",
            "short": {"target": "만 19~29세 GenZ", "benefit": "1위 영역 1.3% 캐시백", "diff": "영역 선택 없는 자동 배정"},
            "benefits": [["1위 영역 캐시백", "1.3% (직전 3개월 이용액 합계 1위 영역)"], ["나머지 2개 영역", "0.4%"], ["적용 조건", "전월 이용실적 30만원 이상인 달 한정, 영역별 월 캐시백 한도 5천원"], ["연회비", "1만원"], ["조건부 환급", "실적 미달 달 산정액의 50%, 직전·다음 달 모두 실적 충족 시 연 1회·회당 3천원 한도"]],
            "target": [["연령", "만 19~29세 (신용카드 발급 가능 연령)"], ["결제 습관", "간편결제(네이버페이·카카오페이·토스페이) 등록, 앱 내 발급·관리 중심"], ["핵심 니즈", "구독·디지털 1순위(가중치 0.85, PM 가정치), 절약·캐시백 2순위"], ["진입 장벽", "금융이력 부족에 따른 발급 심사 문턱, 혜택 불신"]],
            "diffs": [["영역 선택 불필요", "이용 패턴으로 1위 영역을 자동 판정, 선택형·청구할인형 카드와 구분"], ["시판 카드 공백 구조", "시판 카드 34종 중 실적조건 완화·AI 개인화·혜택 풀 공유 구조 0종"], ["판정 규칙 공개", "직전 3개월 합계 기준을 앞·뒷면과 앱에 명시, ‘개인화’ 표현 배제"], ["체리피킹 방어", "3개월 합계 판정, 영역별 월 한도 5천원, 조건부 환급"]],
        },
        "lineup": {
            "newName": "세칸", "newPos": [3.2, 24],
            "own": [["라이프 플러스", 6.5, 36, "30~40대 직장인", "생활 영역 복합 할인"], ["트래블 프리미엄", 8.6, 46, "40~50대 해외 이용", "항공·라운지 복합"], ["데일리 체크", 2.4, 27, "20대 후반 체크카드", "단순 정률 적립"], ["패밀리 케어", 5.6, 41, "30~40대 가족", "생활비·교육 할인"]],
            "compPos": [[6.0, 23], [5.0, 26], [7.0, 29]],
        },
        "doc_head": doc_head,
        "ui": {
            "badge": "실제 LLM 호출 없음 · 2026-10-20 실행 기록 재생",
            "date": "2026-10-20 실행 기록",
            "reresearch": True,
            "researchPrompt": "GenZ 신용카드 시장 흐름과 경쟁 공백을 알려줘",
            "researchSub": "트렌드와 경쟁사를 먼저 병렬로 조사하고, 소비자는 트렌드 시그널이 필요해 그 다음에 불렀습니다. 트렌드와 소비자는 실제 웹 검색을 했고(원문 열람은 막혀 검색 결과 요약과 URL만 사용), 엇갈린 근거 3건은 합치지 않고 총괄 결과에 남겼습니다.",
            "wsSub": "코드가 세그먼트×니즈 기회 점수를 계산하고, 에이전트가 상위 3개를 골라 근거를 썼습니다. 실현가능성 게이트(시장 천장이 충분한지)를 통과한 기회만 골랐습니다. 첫 실행에서 천장 계산 결함이 나와 고친 뒤 GenZ 범위로 다시 계산했습니다.",
            "conceptSub": "에이전트가 서로 다른 3안을 내고, 코드가 손익·유사도·복잡도·채택 의향을 계산했습니다. ‘첫 신용 단계 카드’는 채택 의향이 기준에 못 미쳐 탈락했고, 승자 안은 가드레일 지적을 받아 한 번 재작업했습니다(알아서 맞춤 캐시백 → 많이 쓴 영역 캐시백).",
            "guardSub": "첫 점검에서 fix 3건이 나와 이름 과장(‘알아서 맞춤’이 AI 개인화처럼 읽힘), 문구 오인, 체리피킹 방어를 고쳤습니다(알아서 맞춤 캐시백 → 많이 쓴 영역 캐시백). 아래는 수정 전 점검 결과이고, 사람 확인이 필요한 항목은 담당 부서 확인이 필요합니다.",
            "designNote": "근거가 부족한 3주제는 트렌드 에이전트에 근거 팩 재조사를 1회 요청했고, 끝내 못 찾은 수치는 ‘근거 없음’으로 남겼습니다. 영상은 H5 확정 전이라 렌더하지 않고 스토리보드로 대신합니다.",
            "docNote": "고객 틀 7개 섹션 + 부록으로 작성했습니다. 아래는 앞부분이며 전체는 scenarios/genz-credit/기획서_세칸카드.md에 있습니다.",
            "human": {
                "H1": "해석한 범위: 타깃 GenZ(만 19~29세, 신용카드 발급 가능 연령), 카드 유형 신용카드, 투자 연계는 제외. 이대로 진행할까요?",
                "H2": "상위 3개 셀 중 컨셉을 만들 셀을 고릅니다. 실행 기록에서는 1순위(GenZ × 구독·디지털)를 골랐습니다.",
                "H3": "사람 확인이 필요한 항목을 담당 부서에 배정합니다. 진행은 계속하고 기획서 부록에 미확인으로 남깁니다.",
                "H4": "‘많이 쓴 영역 캐시백 카드’로 확정할까요? 확정하면 이름·디자인·마케팅 단계로 넘어갑니다.",
                "H5": "스토리보드 미리보기를 확인했습니다. 영상은 렌더하지 않고 스토리보드로 대체합니다.",
            },
        },
    }


    if extra:
        DATA.update({k: v for k, v in extra.items() if k not in ("ui", "_guard_final")})
        DATA["ui"] = dict(DATA["ui"], **extra.get("ui", {}))
    return DATA


DATA = build(ROOT / "scenarios" / "genz-credit")
variants = json.loads((ROOT / "scenarios/genz-credit/09-design-marketing/out.json").read_text(encoding="utf-8"))["result"]["boards"]["variants"]
codes = ["A", "B", "C"]
# ---------- 카드 시안 SVG (세칸: NOON / CLEAR / NIGHT) ----------
FF = "Pretendard Variable, Pretendard, Apple SD Gothic Neo, Noto Sans KR, sans-serif"
LIME = "#C8F25A"


def card_svg(code, kor, theme):
    t = THEME[theme]
    u = theme
    bands = [("외식·배달", 150), ("온라인쇼핑", 244), ("구독·디지털", 338)]
    hot = 1  # 가운데 칸을 '이번 달 1위 칸' 예시로 강조 (앞면에는 혜택 숫자를 넣지 않는다)
    b = []
    for k, (lab, y) in enumerate(bands):
        on = k == hot
        fill = t["hot_fill"] if on else t["band_fill"]
        stroke = t["hot_stroke"] if on else t["band_stroke"]
        txt = t["hot_ink"] if on else t["ink"]
        b.append(f'<rect x="30" y="{y}" width="300" height="86" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>')
        b.append(f'<text x="48" y="{y + 34}" font-family="{FF}" font-size="11" font-weight="600" letter-spacing="1.6" fill="{txt}" fill-opacity="0.65">0{k + 1}</text>')
        b.append(f'<text x="48" y="{y + 62}" font-family="{FF}" font-size="19" font-weight="700" fill="{txt}">{lab}</text>')
        if on:
            b.append(f'<rect x="236" y="{y + 20}" width="78" height="24" rx="12" fill="#16181D" fill-opacity="0.92"/>'
                     f'<text x="275" y="{y + 36}" text-anchor="middle" font-family="{FF}" font-size="11" font-weight="700" fill="{LIME}">이번 달 1위 칸</text>')
        else:
            b.append(f'<circle cx="304" cy="{y + 43}" r="6" fill="none" stroke="{txt}" stroke-opacity="0.45" stroke-width="1.4"/>')
    grain = "".join(f'<circle cx="{(37 * i) % 340 + 10}" cy="{(61 * i) % 540 + 10}" r="0.9" fill="#fff" fill-opacity="0.18"/>' for i in range(46)) if t.get("grain") else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 560" width="360" height="560" role="img" aria-label="세칸 카드 시안 {code}: {kor}">'
        f'<defs>'
        f'<linearGradient id="bg{u}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["bg1"]}"/><stop offset="1" stop-color="{t["bg2"]}"/></linearGradient>'
        f'<linearGradient id="shine{u}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="{t["shine"]}"/><stop offset="0.45" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<linearGradient id="chip{u}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t["chip1"]}"/><stop offset="1" stop-color="{t["chip2"]}"/></linearGradient>'
        f'<radialGradient id="glow{u}" cx="0.85" cy="0.1" r="0.7"><stop offset="0" stop-color="{LIME}" stop-opacity="{t["glow"]}"/><stop offset="1" stop-color="{LIME}" stop-opacity="0"/></radialGradient>'
        f'<clipPath id="cp{u}"><rect width="360" height="560" rx="28"/></clipPath></defs>'
        f'<g clip-path="url(#cp{u})"><rect width="360" height="560" fill="url(#bg{u})"/>'
        f'<rect width="360" height="560" fill="url(#glow{u})"/>{grain}'
        f'<polygon points="0,0 250,0 0,330" fill="url(#shine{u})"/></g>'
        f'<rect x="1" y="1" width="358" height="558" rx="27" fill="none" stroke="{t["edge"]}" stroke-width="2"/>'
        f'<rect x="30" y="40" width="54" height="40" rx="8" fill="url(#chip{u})"/>'
        f'<path d="M30 54H84M30 66H84M52 40V80M62 40V80" stroke="#7a5f1e" stroke-opacity="0.45" stroke-width="1"/>'
        f'<g fill="none" stroke="{t["ink"]}" stroke-opacity="0.7" stroke-width="2.4" stroke-linecap="round">'
        f'<path d="M296 48c8 6 8 18 0 24"/><path d="M306 42c13 10 13 30 0 36"/><path d="M316 36c18 14 18 42 0 48"/></g>'
        + "".join(b) +
        f'<text x="30" y="490" font-family="{FF}" font-size="46" font-weight="800" letter-spacing="-1.5" fill="{t["ink"]}">세칸</text>'
        f'<text x="32" y="514" font-family="{FF}" font-size="12.5" font-weight="500" fill="{t["ink"]}" fill-opacity="0.72">평소처럼, 한 장으로.</text>'
        f'<text x="330" y="514" text-anchor="end" font-family="{FF}" font-size="10" font-weight="600" letter-spacing="1.4" fill="{t["ink"]}" fill-opacity="0.55">[ISSUER]</text>'
        f'<text x="330" y="490" text-anchor="end" font-family="{FF}" font-size="10" font-weight="700" letter-spacing="2" fill="{t["ink"]}" fill-opacity="0.55">{code}</text>'
        f'</svg>')


THEME = {
    "A": dict(bg1="#FBF8F0", bg2="#E4DDCB", ink="#16181D", shine="0.55", chip1="#F6E7B4", chip2="#C9A24A", glow="0.0", edge="#ffffff",
              band_fill="#ffffff", band_stroke="#16181D", hot_fill=LIME, hot_stroke="#16181D", hot_ink="#16181D"),
    "B": dict(bg1="#F1FFD0", bg2="#BCE35A", ink="#16181D", shine="0.7", chip1="#E9EEF2", chip2="#9AA7B0", glow="0.35", edge="#ffffff",
              band_fill="#ffffff", band_stroke="#ffffff", hot_fill="#16181D", hot_stroke="#16181D", hot_ink="#F4F1EA"),
    "C": dict(bg1="#34437F", bg2="#0C1230", ink="#F4F1EA", shine="0.22", chip1="#F2DE9B", chip2="#B98E2E", glow="0.35", edge="#6f7fc4", grain=1,
              band_fill="#ffffff", band_stroke="#9fb0ff", hot_fill=LIME, hot_stroke=LIME, hot_ink="#16181D"),
}
import os
for k, v in zip(codes, variants):
    if not os.environ.get("REGEN_CARDS"):
        break  # 카드 시안 SVG는 Opus 5.5가 만든 실물형 시안을 사용한다(ui/assets/genz_design_*.svg). 기본 도형 시안 재생성은 REGEN_CARDS=1
    theme = k
    if k == "B":
        band = THEME["B"]; band["band_fill"] = "#ffffff"
    svg = card_svg(v["code"], v["name"], theme)
    # 반투명 칸은 투명도로 표현
    if k in ("B", "C"):
        svg = svg.replace('fill="#ffffff" stroke="#ffffff" stroke-width="1.2"', 'fill="#ffffff" fill-opacity="0.38" stroke="#ffffff" stroke-opacity="0.9" stroke-width="1.2"')
        svg = svg.replace('fill="#ffffff" stroke="#9fb0ff" stroke-width="1.2"', 'fill="#ffffff" fill-opacity="0.07" stroke="#9fb0ff" stroke-opacity="0.55" stroke-width="1.2"')
    if k == "A":
        svg = svg.replace('fill="#ffffff" stroke="#16181D" stroke-width="1.2"', 'fill="#ffffff" fill-opacity="0.55" stroke="#16181D" stroke-opacity="0.28" stroke-width="1.2"')
    (UI / "assets" / f"genz_design_{k}.svg").write_text(svg, encoding="utf-8")

ALT_DIR = ROOT / "scenarios" / "genz-credit-alt"
DATA_ALT = None
if (ALT_DIR / "10-plan-doc" / "out.json").exists():
    extra = json.loads((ALT_DIR / "ui_extra.json").read_text(encoding="utf-8"))
    extra["_guard_final"] = True
    DATA_ALT = build(ALT_DIR, extra)
(UI / "genz-data.js").write_text("window.DATA_GENZ=" + json.dumps(DATA, ensure_ascii=False) + ";\n" + ("window.DATA_GENZ_ALT=" + json.dumps(DATA_ALT, ensure_ascii=False) + ";\n" if DATA_ALT else ""), encoding="utf-8")
print("ok", (UI / "genz-data.js").stat().st_size, "bytes")
