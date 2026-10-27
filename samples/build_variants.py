#!/usr/bin/env python3
"""선정 카드의 조건(연회비·영역별 월 한도·혜택률 배수·전월실적·교통 추가)을 바꿔 가며 가상 고객 시뮬레이션을 미리 돌려 둔 표를 만든다.
사용자가 확인 질문에 답하며 조건을 바꾸면 화면이 이 표에서 값을 찾아 최종 제안과 수치를 갱신한다(실제 계산 결과).
  python3 samples/build_variants.py <시나리오 폴더 이름>   → scenarios/<이름>/variants.json
모형은 해당 시나리오의 harness.py(가정 기반 가상 고객 모형) 그대로다. 졸업 규칙·앱 기능·예산 조건은 반영하지 못한다."""
import importlib.util, itertools, json, os, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
name = sys.argv[1]
D = os.path.join(ROOT, "scenarios", name)
spec = importlib.util.spec_from_file_location("harness_" + name.replace("-", "_"), os.path.join(D, "harness.py"))
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)
ev = json.load(open(os.path.join(D, "06-concept/eval.json"), encoding="utf-8"))
w = ev["winner"]
base = dict(w["card"], cx=w["metrics"]["appliedCx"])
novelty = w["metrics"]["novelty"]
tgt = H.SC["scope"]["target_segment"]
cats = H.SC["categories"]
rates0 = dict(base["rates"])


def around(v, extra):
    return sorted({round(x, 3) for x in list(extra) + [v]})


KNOBS = {
    "fee": around(base.get("fee", 0), [0, 0.3, 0.5, 1, 1.5]),
    "cap": around(base.get("capPerCat", 0.5), [0.3, 0.4, 0.5, 0.7]),
    "rateMul": around(1.0, [0.8, 1.2, 1.5]),
    "minPerf": around(base.get("minPerf", 0), [0, 10, 15, 20, 30]),
}
# 추가 혜택 영역: 기본 카드가 안 쓰는 카테고리 중 월 소비가 큰 것 2개를 1%로 붙이는 선택지
seg = H.SEG[tgt]
extra_cats = [c for c in sorted(seg["monthly_spend"], key=lambda c: -seg["monthly_spend"][c]) if c not in rates0][:2]
KNOBS["add"] = ["none"] + extra_cats


def make(fee, cap, rm, mp, add):
    rates = {c: min(0.03, r * rm) for c, r in rates0.items()}
    if add != "none":
        rates[add] = 0.01
    return dict(base, fee=fee, capPerCat=cap, rates=rates, minPerf=mp)


def metrics(card):
    tw = H.twin_for(card, novelty)
    bt = tw["by_type"]
    ch = bt.get("혜택 사냥꾼(체리피커)") or {}
    return {"adopt": tw["target_adopt"], "adopterProfit": tw["adopter_profit"], "staticProfit": tw["static_profit"],
            "cherryShare": ch.get("share_of_adopters"), "cherryProfit": ch.get("profit"),
            "scen": [s["adopt"] for s in tw["scenarios"]], "byType": {k: [v["share_of_adopters"], v["profit"]] for k, v in bt.items()}}


t0 = time.time()
grid = {}
for fee, cap, rm, mp, add in itertools.product(KNOBS["fee"], KNOBS["cap"], KNOBS["rateMul"], KNOBS["minPerf"], KNOBS["add"]):
    grid["|".join(map(str, (fee, cap, rm, mp, add)))] = metrics(make(fee, cap, rm, mp, add))
bk = "|".join(map(str, (round(base.get("fee", 0), 3), round(base.get("capPerCat", 0.5), 3), 1.0, round(base.get("minPerf", 0), 3), "none")))
out = {"path": name, "card": w["card"]["working_title"], "base_key": bk, "base_card": {k: base[k] for k in ("fee", "capPerCat", "minPerf", "rates", "tags", "cx")},
       "knobs": KNOBS, "knobs_str": {k: [str(x) for x in v] for k, v in KNOBS.items()}, "cats": cats,
       "target_adopt": H.SC["scope"]["target_adopt"], "behav_floor": H.P["behav_floor"], "profit_floor": 3,
       "scenario_names": ["기본", "경쟁사 모방", "혜택 20% 축소", "시장 위축"], "grid": grid}
json.dump(out, open(os.path.join(D, "variants.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("ok", name, len(grid), "조합", round(time.time() - t0, 1), "초", os.path.getsize(os.path.join(D, "variants.json")) // 1024, "KB", "base", bk, KNOBS)
