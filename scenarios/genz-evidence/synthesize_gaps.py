#!/usr/bin/env python3
"""공백 후보 31개 + 검증 3렌즈 투표 → whitespace_candidates.json.
규칙(코드): 어느 렌즈든 조정 강도가 '폐기'면 탈락. 그 외에는 조정 강도의 중앙값으로 등급(중앙값 2=유력, 1=후보).
같은 아이디어는 병합(MERGE)하되 병합 전 후보와 투표를 모두 남긴다. 병합 묶음은 사람이 정한 표(아래)다."""
import glob, json, os, re
H = os.path.dirname(os.path.abspath(__file__))
L = lambda p: json.load(open(os.path.join(H, p), encoding="utf-8"))
cands = {}
for f in sorted(glob.glob(os.path.join(H, "raw/gap_*.json"))):
    for c in json.load(open(f, encoding="utf-8"))["candidates"]:
        cands[c["id"]] = c
V = {k: {x["candidate_id"]: x for x in L(f"raw/verify_{k}.json")["checks"]} for k in ("existing", "evidence", "risk")}
S = {"강": 3, "중": 2, "약": 1, "폐기": 0}
MERGE = {  # 대표 후보: 같이 합칠 후보 (대표의 서술을 쓰고 나머지는 근거·반증만 합친다)
    "ENC2": [], "ENC1": [], "CTC4": ["VLC5"], "CTC1": ["TPC3"], "CTC3": [], "CTC6": ["TPC4"], "ENC3": [], "TPC1": [], "VLC2": ["ENC5"],
    "VLC1": [], "VLC3": [], "VLC4": ["SOC5"], "VLC6": [], "SOC1": [], "SOC6": [], "CTC5": [],
}
DROP_REASON = {"TPC6": "이미 있음(디지로카 London 즉시결제·Weekly 자동결제)", "CTC2": "결제일 분할은 이미 있음(디지로카 London)", "ENC4": "미성년 대상, 가족카드 승계는 규제·근거 모두 약함",
               "ENC6": "미성년 대상, 근거(SNF16)가 SNF18로 대체됨", "SOC2": "카카오뱅크 모임 체크카드가 실적 없이 풀고 있고, 비가족 합산은 악용·개인정보 문제", "SOC3": "정산 반영 수요 근거 없음(근거 부족)",
               "SOC4": "신한카드 친구추천 캐시백이 이미 있음", "TPC2": "근거가 쿠폰·카드 충돌 수요를 말하지 않음", "TPC5": "건당 금액 근거 없음", "VLC7": "희소성 마케팅은 소비 조장 위험·근거 1건", "ENC5": "VLC2에 병합"}
def ev(ids):
    return sorted({"ev:" + i for i in ids})
def fact_ids_of(c):
    txt = json.dumps(c, ensure_ascii=False)
    return sorted(set(re.findall(r"\b(?:ST|TR|CS|CA|CB|GC|WT|SN|GT|VR|MH|IV)[FTR]?\d+\b", txt)) & ITEMS)
ITEMS = {i["id"] for i in L("evidence_items.json")["items"]}
out, dropped = [], []
for cid, c in cands.items():
    adj = [S[V[k][cid]["adjusted_strength"]] for k in V]
    votes = {k: V[k][cid]["vote"] for k in V}
    if 0 in adj or cid in DROP_REASON:
        dropped.append({"id": cid, "title": c["title"], "reason": DROP_REASON.get(cid, "검증 렌즈가 폐기로 조정"), "votes": votes, "adjusted": dict(zip(V, adj))})
for rep, others in MERGE.items():
    members = [rep] + others
    adj_all = [S[V[k][m]["adjusted_strength"]] for m in members for k in V]
    if 0 in [S[V[k][rep]["adjusted_strength"]] for k in V]:
        continue
    adj_rep = sorted(S[V[k][rep]["adjusted_strength"]] for k in V)
    med = adj_rep[1]
    c = cands[rep]
    verdicts = {m: cands[m]["existing_check"]["verdict"] for m in members}
    found = [f for m in members for f in V["existing"][m]["findings"]]
    out.append({
        "id": "W-" + rep, "tier": "유력(중)" if med >= 2 else "후보(약)", "title": c["title"], "gap_type": c["gap_type"],
        "unmet_need": c["unmet_need"], "mechanism_tags": c["mechanism_tags"], "need_key": c["need_key"], "domain_key": c["domain_key"],
        "evidence_item_ids": ev(set(fact_ids_of(c)) | {i for m in others for i in fact_ids_of(cands[m])}),
        "existing_check": c["existing_check"], "existing_verdicts": verdicts,
        "verification": {"votes": {m: {k: V[k][m]["vote"] for k in V} for m in members}, "adjusted": {k: V[k][rep]["adjusted_strength"] for k in V},
                         "corrections": [x for m in members for k in V for x in V[k][m].get("corrections", [])],
                         "existing_findings": found[:8], "risk_findings": [x for m in members for x in V["risk"][m]["findings"]][:6]},
        "counter_evidence": c["counter_evidence"], "risks": c["risks"], "invest_related": c.get("invest_related", False),
        "cvp_seed": c["cvp_seed"], "merged_from": members, "source_strength": c["strength"],
    })
out.sort(key=lambda w: (0 if w["tier"].startswith("유력") else 1, -sorted(S[w["verification"]["adjusted"][k]] for k in V)[1], -min(S[w["verification"]["adjusted"][k]] for k in V), w["id"]))
for i, w in enumerate(out, 1):
    w["rank"] = i
inv = L("raw/invest.json")
invest_refs = [{"id": h["id"], "hypothesis": h["hypothesis"], "strength": h["strength"], "counter_evidence": h["counter_evidence"]} for h in inv["whitespace_hypotheses"]]
res = {"as_of": "2026-10-23", "method": "각도 5개가 후보 31개를 냈고, 렌즈 3개(기존 시판 반증, 근거 정합성, 규제·수익성·악용)가 각각 투표했다. 어느 렌즈든 폐기로 조정하면 탈락, 나머지는 조정 강도 중앙값으로 등급. 강으로 남은 후보 없음.",
       "candidates": out, "dropped": dropped,
       "invest": {"verdict": "투자 연계는 이미 존재하고(카카오페이 동전 모으기 등) 신용카드로 금융투자상품을 결제할 수 없다(여전법 시행령 제1조의2). 20대의 카드-투자 연계 수요 근거 없음. 후보에서 제외하고 규칙만 CVP에 전달.",
                  "hypotheses": invest_refs, "rules": [{"id": c["id"], "rule": c["rule"], "status": c["status"]} for c in inv["constraints"]]}}
json.dump(res, open(os.path.join(H, "whitespace_candidates.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(out), "candidates;", len(dropped), "dropped")
for w in out:
    print(w["rank"], w["id"], w["tier"], w["mechanism_tags"], w["need_key"], w["domain_key"], "| ev", len(w["evidence_item_ids"]), "|", w["title"][:50])
