#!/usr/bin/env python3
"""GenZ 시나리오 v2 팩을 만든다: scenario.json, competitor_db.json(50종 + 새 태그), evidence/(탐색 파이프라인 결과).
v1(scenarios/genz-credit)은 건드리지 않는다. 바뀐 가정은 모두 scenario.json 의 notes 에 적는다.
  PYTHONPATH=runtime python3 scenarios/genz-credit-v2/make_scenario.py"""
import copy, json, os, shutil, sys
H = os.path.dirname(os.path.abspath(__file__))
MVP = os.path.dirname(os.path.dirname(H))
sys.path.insert(0, os.path.join(MVP, "runtime"))
L = lambda p: json.load(open(os.path.join(H, p), encoding="utf-8"))
W = lambda p, d: (os.makedirs(os.path.dirname(os.path.join(H, p)) or H, exist_ok=True), json.dump(d, open(os.path.join(H, p), "w", encoding="utf-8"), ensure_ascii=False, indent=2))

base = json.load(open(os.path.join(H, "../genz-credit/scenario.json"), encoding="utf-8"))
new_tags = L("new_tags.json")
retag = L("db_retag.json")["cards"]

sc = copy.deepcopy(base)
sc.update(run_id="genz-credit-v2-001", today="2026-10-23", request="GenZ 특화 신용카드 만들어줘", mode="workflow",
          note="E2E 상품기획 시나리오 v2. 근거는 scenarios/genz-evidence 근거 팩(사실 524건, 출처 257건)이고, 탐색 파이프라인(scenarios/genz-discovery)이 공백 후보와 컨셉 아이디어를 냈다.")
sc["scope"] = {
    "target_segment": "genz", "target_segment_name": "GenZ(만 19~29세)", "card_type": "신용카드", "target_adopt": 0.38,
    "constraints": ["신용카드 발급 가능 연령(만 19세 이상, 가족카드는 부모 동의 예외)", "신용카드로 금융투자상품은 결제할 수 없다(여전법 시행령 제1조의2)",
                    "투자 연계는 이번 시나리오에서 제외(근거 팩 조사에서 특이한 공백도, 20대 수요 근거도 찾지 못함)", "혜택률 0 초과 3% 이하, 연회비 0~2만원(가정치)"],
    "allow_invest": False,
    "assumptions": ["GenZ를 기준일 2026-10-23 기준 1997~2007년생 중 신용카드 발급이 가능한 만 19~29세로 해석(조사는 잘파·Z세대·젊은층까지 넓혔고 근거마다 age_scope 표시)",
                    "고객사 회원·결제 데이터 없이 공개 자료와 PM 가정치로 진행. 20대 카테고리별 월 소비는 공개 통계로 확인하지 못해 월 소비 수치는 계속 가정치",
                    "목표 채택 의향 0.38은 기존 리허설과 같은 PM 가정치"]}
sc["segments"] = [s for s in sc["segments"] if s["id"] in ("genz", "young")]
CTRL = {"genz": 0.7, "young": 0.65}
for s in sc["segments"]:
    s["need_weights"]["control"] = CTRL[s["id"]]
sc["need_labels"]["control"] = "소비 통제·예측 가능성"
nm = sc["need_tag_map"]
nm["control"] = ["self_budget_cap", "budget_keep_bonus", "subscription_ledger", "zero_floor", "single_exclusion_perf"]
nm["saving"] += ["first_try_reward", "habit_conversion", "value_spend_reward", "post_purchase_pick"]
nm["digital"] += ["subscription_slot", "seasonal_slot", "experience_category_pack", "evergreen_fallback"]
nm["social"] += ["crew_vote_category"]
nm["simple"] += ["perf_graduation"]
sc["incidents"] = []
sc["pm_directions"] = json.load(open(os.path.join(H, "../genz-discovery/discovery.json"), encoding="utf-8"))["pm_directions"]   # H1 범위 확인에서 PM이 밝힌 관심 방향(05 입력)
sc["v2_notes"] = {
    "added_need": "control(소비 통제·예측 가능성). 근거: MZ 설문 소비 통제 64.4% vs 혜택 설계 19.2%(CSF5, 표본·기간 미기재, 20대 단독 아님). 가중치 genz 0.7, young 0.65는 PM 가정치",
    "removed_segment": "single(타깃 밖)",
    "new_tags": "탐색 파이프라인 데모 후보가 필요로 한 혜택 방식 15개. 니즈 연결(need_tag_map)은 PM 가정치",
    "unchanged_assumptions": "월 소비, 복잡도 허용도, 기존 니즈 가중치, 시뮬레이션 계수(sim_params)는 v1과 같은 PM 가정치",
}
W("scenario.json", sc)

# 경쟁 카드 DB: 50종(공식 페이지 기준) + 새 태그. 새 태그는 db_retag.json 에서 근거가 확인된 1종에만 붙었다.
db = json.load(open(os.path.join(H, "../genz-evidence/competitor_db.enriched.json"), encoding="utf-8"))
allowed = dict(db["allowed_tags"])
for t in new_tags:
    allowed[t["key"]] = t["label"]
cards = []
for c in db["cards"]:
    c = copy.deepcopy(c)
    c["tags"] = c["tags"] + [t for t in retag.get(c["id"], {}).get("tags_add", []) if t not in c["tags"]]
    fee = c.get("annual_fee")
    c["annual_fee"] = None if fee is None else f"{fee:g}만원"
    cards.append(c)
W("competitor_db.json", {"as_of": "2026-10-23", "allowed_tags": allowed, "new_tag_definitions": new_tags, "cards": cards})

# 탐색 파이프라인 결과(replay) → evidence/
from cardstudio.config import Settings
from cardstudio.discovery import Discovery
from cardstudio.hitl import HumanGate
fin = json.load(open(os.path.join(H, "../genz-evidence/ideas_ranked.json"), encoding="utf-8"))["finalists"]
s = Settings(provider="replay", human_mode="auto")
shutil.rmtree(os.path.join(s.runs_dir, "_mk_v2"), ignore_errors=True)
d = Discovery(s, "_mk_v2", os.path.join(H, "../genz-discovery/discovery.json"), human=HumanGate("auto", None, {"HD1": {"id": "manual", "finalists": fin}}))
res = d.execute()
ev = os.path.join(H, "evidence")
shutil.rmtree(ev, ignore_errors=True)
shutil.copytree(os.path.join(d.dir, "discovery_pack"), ev)
shutil.rmtree(d.dir)
db2 = {"as_of": "2026-10-23", "allowed_tags": allowed, "cards": cards}
json.dump(db2, open(os.path.join(ev, "competitor_db.enriched.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("scenario ok; finalists", res["finalists"], "tags", len(allowed), "cards", len(cards))
