#!/usr/bin/env python3
"""raw/ 조사 결과를 합쳐 근거 팩 산출물을 만든다. 조사 내용을 바꾸지 않고 모양만 맞춘다(계산·추정 없음).
  python3 build_pack.py  →  sources.json, facts.json, competitor_db.enriched.json, trends.candidates.json, consumer.candidates.json"""
import json, os
H = os.path.dirname(os.path.abspath(__file__))
L = lambda p: json.load(open(os.path.join(H, p), encoding="utf-8"))
W = lambda p, d: json.dump(d, open(os.path.join(H, p), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
RAW = ("stats", "trends", "competitor_a", "competitor_b", "genz_cards", "consumer", "wide", "suneung", "gatherings", "viral", "money", "invest")
raws = {n: L(f"raw/{n}.json") for n in RAW}
base = L("../../samples/03-competitor/in.sample.json")["payload"]
allowed = base["allowed_tags"]

# ---- 출처·사실 합치기 (id 접두가 담당마다 달라 충돌 없음)
sources, facts, seen = [], [], set()
for n, d in raws.items():
    for s in d["sources"]:
        assert s["id"] not in seen, s["id"]
        seen.add(s["id"]); sources.append(dict(s, collected_by=n))
    for f in d["facts"]:
        facts.append(dict(f, collected_by=n))
sid = {s["id"]: s for s in sources}
for f in facts:
    assert f["source_id"] in sid, f["id"]
W("sources.json", {"retrieved_at": "2026-10-23", "sources": sources})
W("facts.json", {"retrieved_at": "2026-10-23", "facts": facts})

# ---- 경쟁 카드 DB 보강: 기존 34종(태그 유지) + 신규 16종(태그는 별도 태깅)
tags_new = {c["id"]: c for c in L("raw/genz_cards_tags.json")["cards"]}
enrich = {c["id"]: c for n in ("competitor_a", "competitor_b") for c in raws[n]["cards"]}
cards = []
def first_url(ids):
    for i in ids or []:
        if i in sid and sid[i].get("url"):
            return sid[i]["url"]
    return None
for c in base["competitor_db"]["cards"]:
    e = enrich[c["id"]]
    fee = (e.get("annual_fee_won") or {}).get("domestic")
    cards.append(dict(c, official_name=e.get("official_name"), on_sale=e.get("on_sale"), annual_fee=None if fee is None else fee / 10000,
                      annual_fee_won=e.get("annual_fee_won"), min_prev_month_spend_won=e.get("min_prev_month_spend_won"),
                      headline_benefits=e.get("headline_benefits", []), explicit_target_text=e.get("explicit_target_text"),
                      genz_fit=e.get("genz_fit"), genz_fit_reason=e.get("genz_fit_reason"), source_url=first_url(e.get("source_ids")),
                      source_ids=e.get("source_ids", []), as_of=e.get("as_of"), origin="기존 DB(보강)", note=e.get("note", "")))
for c in raws["genz_cards"]["cards"]:
    t = tags_new[c["id"]]
    fee = (c.get("annual_fee_won") or {}).get("domestic")
    youth = bool(c.get("explicit_target_text"))
    cards.append({"id": c["id"], "name": c["name"], "issuer": c["issuer"], "type": c["type"], "target": "young" if youth else "free",
                  "tags": t["tags"], "tag_basis": t["tag_basis"], "tag_confidence": t["tag_confidence"], "is_own": False,
                  "official_name": c.get("official_name"), "on_sale": c.get("on_sale"), "annual_fee": None if fee is None else fee / 10000,
                  "annual_fee_won": c.get("annual_fee_won"), "min_prev_month_spend_won": c.get("min_prev_month_spend_won"),
                  "headline_benefits": c.get("headline_benefits", []), "explicit_target_text": c.get("explicit_target_text"),
                  "genz_fit": "high" if youth else "medium", "genz_fit_reason": c.get("distinct_feature"),
                  "source_url": first_url(c.get("source_ids")), "source_ids": c.get("source_ids", []), "as_of": c.get("as_of"),
                  "origin": f"신규 스캔({c.get('category_in_scan')})", "note": c.get("note", "")})
assert all(t in allowed for c in cards for t in c["tags"])
W("competitor_db.enriched.json", {"as_of": "2026-10-23", "allowed_tags": allowed, "cards": cards})

# ---- 트렌드·소비자 후보(02/04 입력 재료)
W("trends.candidates.json", {"signals": raws["trends"]["signals"], "gaps": raws["trends"]["gaps"]})

# ---- 근거 색인 항목(라벨 전): 에이전트가 ev:<id> 로 인용하는 단위
def src_info(ids):
    for i in ids or []:
        if i in sid:
            return sid[i]
    return {}
items = []
for f in facts:
    s_ = sid[f["source_id"]]
    items.append({"id": f["id"], "kind": "fact", "text": f["claim"], "population": f.get("population"), "period": f.get("period"),
                  "age_scope": f.get("age_scope") or ("20대" if "20대" in (f.get("population") or "") else None), "source_ids": [f["source_id"]],
                  "source_title": s_.get("title"), "published": s_.get("published"), "confidence": f.get("confidence"),
                  "stale": bool(s_.get("stale")), "promotional": bool(s_.get("promotional")), "topic": f.get("topic"), "out_of_scope": bool(f.get("out_of_scope"))})
for n, d in raws.items():
    for t in d.get("trend_items", []):
        s_ = src_info([sid_ for fid in t["fact_ids"] for sid_ in [next((x["source_id"] for x in facts if x["id"] == fid), None)] if sid_])
        items.append({"id": t["id"], "kind": "trend", "text": t["title"] + ". " + t["what"], "age_scope": t.get("age_scope"), "source_ids": sorted({x["source_id"] for x in facts if x["id"] in t["fact_ids"]}),
                      "source_title": s_.get("title"), "published": t.get("when"), "confidence": None, "stale": False, "durability": t.get("durability"),
                      "virality": t.get("virality"), "interpretation": t.get("card_relevance"), "fact_ids": t["fact_ids"], "topic": ",".join(t.get("categories", []))})
for t in raws["trends"]["signals"]:
    items.append({"id": t["id"], "kind": "trend", "text": t["title"] + ". " + t["summary"], "age_scope": t.get("genz_specificity"), "source_ids": [],
                  "source_title": None, "published": None, "confidence": None, "stale": False, "interpretation": t.get("card_relevance"), "fact_ids": t["fact_ids"], "topic": t.get("topic")})
for t in raws["consumer"]["themes"]:
    items.append({"id": t["id"], "kind": "theme", "text": t["theme"] + ". " + t["summary"], "age_scope": None, "source_ids": [], "source_title": None,
                  "published": None, "confidence": None, "stale": False, "fact_ids": t["fact_ids"], "topic": t.get("strength")})
for v in raws["consumer"]["voices"]:
    items.append({"id": v["id"], "kind": "voice", "text": v["text"], "age_scope": None, "source_ids": [v["source_id"]], "source_title": sid[v["source_id"]]["title"],
                  "published": sid[v["source_id"]].get("published"), "confidence": "low", "stale": bool(sid[v["source_id"]].get("stale")), "topic": v.get("note")})
for c in raws["invest"].get("cases", []):
    items.append({"id": c["id"], "kind": "case", "text": f"{c['name']}({c['operator']}, {c.get('launched')}, 상태 {c['status']}): {c['structure']}" + (f" 지표: {c['metrics']}" if c.get("metrics") else ""),
                  "age_scope": None, "source_ids": c["source_ids"], "source_title": src_info(c["source_ids"]).get("title"), "published": c.get("launched"),
                  "confidence": None, "stale": c["status"] in ("ended", "unknown"), "topic": c["type"]})
for c in raws["invest"].get("constraints", []):
    items.append({"id": c["id"], "kind": "constraint", "text": c["rule"] + (f" ({c['note']})" if c.get("note") else ""), "age_scope": None,
                  "source_ids": c["source_ids"], "source_title": src_info(c["source_ids"]).get("title"), "published": c.get("as_of"),
                  "confidence": None, "stale": False, "topic": c.get("status")})
ids_ = [i["id"] for i in items]
assert len(ids_) == len(set(ids_)), [k for k in set(ids_) if ids_.count(k) > 1]
W("evidence_items.json", {"items": items})
W("consumer.candidates.json", {"themes": raws["consumer"]["themes"], "voices": raws["consumer"]["voices"], "gaps": raws["consumer"]["gaps"]})

import collections
cnt_old = collections.Counter(t for c in cards[:34] for t in c["tags"])
cnt_all = collections.Counter(t for c in cards for t in c["tags"])
print("sources", len(sources), "facts", len(facts), "cards", len(cards))
for t in ["ai_personalize", "miss_refund", "anti_cap", "social", "group_pooling", "challenge", "auto_best", "life_event", "esg_green", "benefit_rental", "perf_recharge", "select_pack", "monthly_switch", "plcc_brand", "bank_bundle"]:
    print(f"  {t:16s} 34종 {cnt_old[t]} → 50종 {cnt_all[t]}")
