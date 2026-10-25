#!/usr/bin/env python3
"""컨셉 아이디어 32개 + 검증 3렌즈(참신성, 근거·수요, 규제·수익·악용) → ideas_ranked.json.
규칙(코드): 렌즈 등급 A3·B2·C1·X0 합산. 어느 렌즈든 X면 탈락. 같은 아이디어는 병합표(MERGE)로 합쳐 대표만 순위에 올린다(병합된 쪽 투표도 보존).
강한 성립 근거가 없으므로 등급은 '유망/보완 필요'로만 표시하고, 데모 후보(finalists)는 합계·유형 다양성·PM 관심 방향으로 사람이 고른다(FINALISTS)."""
import glob, json, os
H = os.path.dirname(os.path.abspath(__file__))
ideas, theme = {}, {}
for f in sorted(glob.glob(os.path.join(H, "raw/idea_*.json"))):
    d = json.load(open(f, encoding="utf-8"))
    for i in d["ideas"]:
        ideas[i["id"]] = i
        theme[i["id"]] = d["theme"]
V = {k: {x["idea_id"]: x for x in json.load(open(os.path.join(H, f"raw/verify_ideas_{k}.json"), encoding="utf-8"))["checks"]} for k in ("novelty", "evidence", "risk")}
R = {"A": 3, "B": 2, "C": 1, "X": 0}
MERGE = {"GRI6": "TDI4", "TDI6": "GRI5", "PRI4": "GRI7", "PRI5": "FRI1", "PRI1": "PRI2", "TDI7": "FRI2"}   # 키를 값에 병합(대표 = 값)
FINALISTS = {   # 데모 후보와 고른 이유(사람이 정함)
    "GRI1": "졸업·실적 재해석을 한 구조로 묶음. 보증금·미성년 규제에 기대지 않고 약관으로 가능. 검증 렌즈 모두 B",
    "FRI1": "소비 통제(수요 신호가 가장 직접적)와 실적 재해석(예산 밴드)을 합침. PRI5 병합",
    "TDI1": "규제 검증을 유일하게 통과(PFF40 예외와 구조 일치). 다음 유행 연계와 플랫폼 제안 기능(TDI2)의 출발점",
    "FRI8": "참신성 최고(결제 후 고르기). 비용 구조 위험이 가장 커서 가상 고객·가드레일 단계의 시험대",
    "FRI4": "참신성 최고(친구가 함께 혜택 영역을 투표). 수요 근거는 체크카드뿐이라 가장 큰 가설",
    "GRI5": "고객에게 '처음'인 소비에 보상. 참신성 A. TDI6 병합",
    "PRI3": "금감원 2026-07 개선안과 방향이 같은 '투명 실적'. 신뢰형 컨셉",
    "FRI2": "구독 이용률(20대 99.1%)과 맞는 구독 슬롯·장부. TDI7 병합. 착붙 신한카드 등 AI 할인은 이미 있으므로 관리 쪽으로 좁힘",
}
rows = []
for iid, i in ideas.items():
    rt = {k: R[V[k][iid]["rating"][0]] for k in V}
    rows.append({"id": iid, "name": i["name"], "theme": theme[iid], "one_liner": i["one_liner"], "novelty_type": i["novelty_type"],
                 "ratings": rt, "sum": sum(rt.values()), "votes": {k: V[k][iid]["vote"] for k in V},
                 "novelty_verdict": V["novelty"][iid]["lens_fields"].get("novelty_verdict"), "closest_real_card": V["novelty"][iid]["lens_fields"].get("closest_real_card"),
                 "demand_evidence": V["evidence"][iid]["lens_fields"].get("demand_evidence"), "weakest_link": V["evidence"][iid]["lens_fields"].get("weakest_link"),
                 "must_check_first": V["risk"][iid]["lens_fields"].get("must_check_first"), "profit_structure": V["risk"][iid]["lens_fields"].get("profit_structure"),
                 "blocking": V["risk"][iid]["lens_fields"].get("blocking"),
                 "corrections": [c for k in V for c in V[k][iid].get("corrections", [])],
                 "merged_into": MERGE.get(iid), "dropped": 0 in rt.values(), "finalist": FINALISTS.get(iid) is not None, "finalist_reason": FINALISTS.get(iid),
                 "evidence_ids": i["evidence_ids"], "new_tags": i.get("new_tags", []), "need_key": i.get("need_key"), "domain_key": i.get("domain_key"),
                 "concept": i["concept"], "nearest_cards": i["nearest_cards"], "risks": i["risks"], "open_questions": i.get("open_questions", []),
                 "platform_hook": i.get("platform_hook"), "durability": i.get("durability")})
rank = [r for r in rows if not r["merged_into"] and not r["dropped"]]
rank.sort(key=lambda r: (-r["sum"], -r["ratings"]["novelty"], r["id"]))
for k, r in enumerate(rank, 1):
    r["rank"] = k
res = {"as_of": "2026-10-23", "method": "아이디어 32개, 렌즈 3개 등급 합산. A(검증 후에도 유망)는 0개, B 17·C 15는 렌즈별 합산 기준으로 아래 순위. 어느 렌즈든 X면 탈락(해당 없음).",
       "ranking": [{k: r[k] for k in ("rank", "id", "name", "theme", "sum", "ratings", "votes", "novelty_verdict", "finalist")} for r in rank],
       "ideas": rows, "finalists": [r["id"] for r in rank if r["finalist"]],
       "new_tag_proposals": sorted({(t["key"], t["label"], t["definition"]) for r in rows if r["finalist"] for t in r["new_tags"]})}
res["new_tag_proposals"] = [{"key": a, "label": b, "definition": c} for a, b, c in res["new_tag_proposals"]]
json.dump(res, open(os.path.join(H, "ideas_ranked.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for r in rank[:14]:
    print(r["rank"], r["id"], r["sum"], r["ratings"], "F" if r["finalist"] else " ", r["name"][:24], "|", r["novelty_verdict"])
print("finalists", res["finalists"], "new tags", len(res["new_tag_proposals"]))
