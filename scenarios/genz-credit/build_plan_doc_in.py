#!/usr/bin/env python3
"""10 기획서 입력(payload)을 앞 단계 JSON에서 코드로 조립한다. 받는 필드를 열거하고 통째로 넣지 않는다(설계서 10, 3절).
allowed_urls, allowed_numbers, decision_log 는 코드가 만든다."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
L = lambda p: json.load(open(os.path.join(HERE, p), encoding="utf-8"))
sample = json.load(open(os.path.join(HERE, "../../samples/10-plan-doc/in.sample.json"), encoding="utf-8"))["payload"]

rl, tr, cp, cs = (L(f"{p}/out.json") for p in ("01-research-lead", "02-trend", "03-competitor", "04-consumer"))
ws, co, ev = L("05-whitespace/out.json"), L("06-concept/out.json"), L("06-concept/eval.json")
va, gr, dm = L("07-validation/out.json"), L("08-guardrail/out.json"), L("09-design-marketing/out.json")
ws_in = L("05-whitespace/in.json")
te = L("02-trend-evidence/out.json")
win = ev["winner"]

LABEL = {"segId": "타깃 세그먼트", "need": "니즈", "tags": "혜택 유형", "rates": "영역별 캐시백률", "capPerCat": "영역별 월 한도(만원)",
         "fee": "연회비(만원)", "minPerf": "전월 이용실적 기준(만원)", "cx": "복잡도(자기보고)", "links": "그룹사 연계"}
TAG_KO = ws_in["payload"].get("research", {}) and None
allowed_tags = L("03-competitor/in.json")["payload"]["allowed_tags"]
CAT = L("scenario.json")["categories"]


def label_card(card):
    out = {}
    for k, v in card.items():
        if k == "tags":
            v = [allowed_tags.get(t, t) for t in v]
        if k == "rates":
            v = {CAT.get(c, c): r for c, r in v.items()}
        out[LABEL.get(k, k)] = v
    return out


alternatives = []
for r in ev["eval"]:
    if r["i"] == win["metrics"]["i"]:
        continue
    why = "통과 기준 미달: " + ", ".join(r["fails"]) if not r["pass"] else f"통과했으나 종합 점수 {r['score']}로 승자({win['metrics']['score']})보다 낮음"
    alternatives.append({"working_title": r["name"], "reason_dropped": why,
                         "metrics": {k: r[k] for k in ("adopt", "profit", "novelty", "sim", "adopterProfit", "cherry")}})
first = L("06-concept/eval.attempt1.json")["winner"]["metrics"]
alternatives.append({"working_title": first["name"], "reason_dropped": "1차 승자였으나 가드레일 fix 3건(G1 이름·약속 과장, G2 오인 소지 표현, G6 체리피킹)으로 재작업되어 현재 안이 되었다",
                     "metrics": {k: first[k] for k in ("adopt", "profit", "novelty", "sim", "adopterProfit", "cherry")}})

research = {"headline": rl["result"]["headline"], "key_findings": rl["result"]["key_findings"],
            "conflicts": rl["result"]["conflicts"], "uncertainties": rl["result"].get("uncertainties", []),
            "signals": [{k: s[k] for k in ("id", "title", "impl", "reliability", "stale", "research_topic") if k in s} for s in tr["result"]["signals"] + te["result"]["signals"]],
            "competitor": {k: cp["result"][k] for k in ("crowded", "empty", "nearest")},
            "consumer": {k: cs["result"][k] for k in ("top_needs", "must_have", "can_give_up")}}
dmr = dm["result"]
design = {"naming": dmr["naming"],
          "strategy": {k: dmr["strategy"].get(k) for k in ("positioning", "pillars", "channels", "phases", "kpis", "risks") if k in dmr["strategy"]},
          "boards": {"concept": dmr["boards"].get("concept"), "variants": [{k: v.get(k) for k in ("code", "name", "story") if k in v} for v in dmr["boards"].get("variants", [])]},
          "storyboards": {k: {"duration_s": v.get("duration_s"), "scenes": [{kk: sc.get(kk) for kk in ("t", "visual", "caption", "voiceover", "duration_s") if kk in sc} for sc in v.get("scenes", [])]}
                          for k, v in dmr["storyboards"].items()},
          "segment_plays": dmr.get("segment_plays"), "compliance": dmr.get("compliance"), "needs_research": dmr.get("needs_research")}

needs_client_data = [
    {"item": "자사 포트폴리오 분석(카니발라이제이션)", "purpose": "기존 카드 라인업과 이 카드의 잠식·시너지를 계산한다. 필요한 입력: 기존 카드별 타깃·혜택·연회비·회원수, 만 19~29세 고객의 보유 카드와 월 이용액 분포.",
     "fallback": f"공개 시판 카드 34종 대비 새로움 {win['metrics']['novelty']}, 최근접 카드({win['metrics']['nearest']})와의 유사도 {win['metrics']['sim']}"},
    {"item": "BEP(손익분기점)", "purpose": "고정비(개발·마케팅·심사·인건비), 발급 목표, 고객 획득 비용, 해지율, 충당금률을 받아야 계산할 수 있다. 월 단위 BEP 시점은 쓰지 않고 계산식과 필요한 입력만 쓴다.",
     "fallback": f"가상 고객 시뮬레이션의 정적 손익 {win['metrics']['profit']}와 채택 고객 기준 손익 {win['metrics']['adopterProfit']}"},
    {"item": "수익 모델", "purpose": "가맹점 수수료 수익, 예상 취급고, 할부·리볼빙 전환율은 고객사 수치가 필요하다.", "fallback": "시뮬레이션 모형의 수익률 가정(PM 가정치)"},
    {"item": "GenZ 세그먼트 수치", "purpose": "월 소비, 니즈 가중치, 복잡도 허용도는 PM 가정치다. 만 19~29세 회원의 카테고리별 이용액 집계로 바꿔야 한다.", "fallback": "PM 가정치(scenario.json)"},
]
rr_teams = ["마케팅팀: 캠페인 기획, 매체 전략, 홍보 영상 제작 확정",
            "디자인팀: 카드 플레이트와 앱 UI 제작, 후보 3안 중 확정",
            "IT/데이터팀: 영역별 이용액 집계와 직전 3개월 판정, 연간 결제 월할, 조건부 환급 산정, 앱 중간 집계 표시 구축",
            "리스크관리팀: 수익성과 리스크 재검증, 체리피커 행동 가정 검증, 1위 영역 비율과 한도 결정(가드레일 G6)",
            "법무·준법팀: 지급 조건·부가서비스 변경 고지(G3), 결제 내역 활용 동의(G4), 광고 문구 심의(G2)"]

trace = L("trace.json")
keep = {"gate", "human_decision", "rework", "code_fix", "code"}
decision_log = [{"step": e["event"], "event": e["detail"], "effect": e.get("agent") or "-"} for e in trace if e["event"] in keep]


def urls(o):
    return {s["url"] for s in o.get("sources", []) if s.get("url") and not s["url"].startswith("https://card-studio.invalid")}


allowed_urls = sorted(set().union(*(urls(x) for x in (rl, tr, te, cp, cs, ws, co, va, gr, dm))))

payload_core = {"research": research, "opportunity": {"picks": ws["result"]["picks"], "chosen": ws["result"]["picks"][0]},
                "final_card": label_card(win["card"]), "final_metrics": win["metrics"], "alternatives": alternatives,
                "twin": va["result"]["twin"], "voices": va["result"]["voices"], "guardrail": gr["result"], "design_marketing": design}

nums = set()


def walk(o):
    if isinstance(o, bool):
        return
    if isinstance(o, (int, float)):
        nums.add(str(o))
        if 0 < abs(o) <= 1:
            nums.add(f"{o * 100:.1f}%")
            nums.add(f"{o * 100:.0f}%")
    elif isinstance(o, str):
        for m in re.findall(r"\d+(?:\.\d+)?%", o):
            nums.add(m)
        for m in re.findall(r"\d+(?:\.\d+)?", o):
            nums.add(m)
    elif isinstance(o, dict):
        for v in o.values():
            walk(v)
    elif isinstance(o, list):
        for v in o:
            walk(v)


walk(payload_core)
walk(needs_client_data)
walk(rr_teams)
walk(decision_log)

payload = dict(payload_core, template=sample["template"], style=sample["style"], needs_client_data=needs_client_data, rr_teams=rr_teams,
               schedule_note=sample["schedule_note"], allowed_urls=allowed_urls, allowed_numbers=sorted(nums), decision_log=decision_log)
env = L("09-design-marketing/in.json")
env.update({"request_id": "genz-credit-001-plan_doc-r1", "agent": "plan_doc",
            "question": "지금까지 나온 결과를 모아서 7개 섹션 틀로 GenZ 특화 신용카드 기획서를 써줘. 모르는 숫자는 만들지 말고, 고객 데이터가 필요한 건 뭐가 필요한지 적어줘.",
            "payload": payload})
os.makedirs(os.path.join(HERE, "10-plan-doc"), exist_ok=True)
json.dump(env, open(os.path.join(HERE, "10-plan-doc/in.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("urls", len(allowed_urls), "numbers", len(nums), "decisions", len(decision_log))
