"""scout 결과(출처·사실·트렌드·사례·제약·예측) → 근거 색인 항목 → 라벨 적용 → evidence_index.json.
조사 내용을 바꾸지 않고 모양만 맞춘다(계산·추정 없음). 인용 단위 id 는 담당 접두가 달라 충돌하지 않는다."""
from __future__ import annotations

import json
import os

TIER_RELIABILITY = {"A": 0.9, "B": 0.7, "C": 0.5, "D": 0.3}


def merge_scout_results(results: dict) -> dict:
    """results: {topic: 봉투 out(sources + result)} → {sources, facts, trend_items, cases, constraints, predictions, design_analogues}"""
    out = {"sources": [], "facts": [], "trend_items": [], "cases": [], "constraints": [], "predictions": [], "design_analogues": [], "voices": [], "themes": []}
    seen = {k: set() for k in out}
    for topic, env in results.items():
        for s in env.get("sources", []):
            out["sources"].append(dict(s, collected_by=topic))
        for k in out:
            if k == "sources":
                continue
            for x in env["result"].get(k, []):
                if x["id"] in seen[k]:
                    raise ValueError(f"{k} id 충돌: {x['id']} (id_prefix 를 담당마다 다르게)")
                seen[k].add(x["id"])
                out[k].append(dict(x, collected_by=topic))
    return out


def build_items(merged: dict, extra_items: list | None = None) -> list[dict]:
    sid = {s["id"]: s for s in merged["sources"]}
    facts_by_id = {f["id"]: f for f in merged["facts"]}
    items = []
    for f in merged["facts"]:
        s_ = sid.get(f["source_id"], {})
        promo = s_.get("tier") == "D" or bool(s_.get("promotional"))   # SC-R7: 홍보성(tier D) 출처의 사실은 신뢰도를 low 로 낮추고 근거 검색에서 감점
        items.append({"id": f["id"], "kind": "fact", "text": f["claim"], "population": f.get("population"), "period": f.get("period"),
                      "age_scope": f.get("age_scope") or ("20대" if "20대" in (f.get("population") or "") else None), "source_ids": [f["source_id"]],
                      "source_title": s_.get("title"), "published": s_.get("published"), "confidence": "low" if promo else f.get("confidence"),
                      "stale": bool(s_.get("stale")), "promotional": promo, "topic": f.get("topic"), "out_of_scope": bool(f.get("out_of_scope"))})
    for t in merged["trend_items"]:
        srcs = sorted({facts_by_id[x]["source_id"] for x in t["fact_ids"] if x in facts_by_id})
        s_ = sid.get(srcs[0], {}) if srcs else {}
        items.append({"id": t["id"], "kind": "trend", "text": t["title"] + ". " + t["what"], "age_scope": t.get("age_scope"), "source_ids": srcs,
                      "source_title": s_.get("title"), "published": t.get("when"), "confidence": None, "stale": False, "durability": t.get("durability"),
                      "virality": t.get("virality"), "phase": t.get("phase"), "interpretation": t.get("card_relevance"), "fact_ids": t["fact_ids"],
                      "topic": ",".join(t.get("categories", []))})
    for c in merged["cases"]:
        s_ = sid.get(c["source_ids"][0], {})
        items.append({"id": c["id"], "kind": "case", "text": f"{c['name']}({c.get('operator', '')}, {c.get('launched')}, 상태 {c.get('status')}): {c['structure']}"
                      + (f" 지표: {c['metrics']}" if c.get("metrics") else "") + (f" 한계: {c['limits']}" if c.get("limits") else ""),
                      "age_scope": None, "source_ids": c["source_ids"], "source_title": s_.get("title"), "published": c.get("launched"), "confidence": None,
                      "stale": c.get("status") in ("ended", "unknown"), "topic": c.get("kind") or c.get("type")})
    for c in merged["constraints"]:
        s_ = sid.get(c["source_ids"][0], {})
        items.append({"id": c["id"], "kind": "constraint", "text": c["rule"] + (f" ({c['note']})" if c.get("note") else ""), "age_scope": None,
                      "source_ids": c["source_ids"], "source_title": s_.get("title"), "published": c.get("as_of"), "confidence": None, "stale": False, "topic": c.get("status")})
    for p in merged["predictions"]:
        items.append({"id": p["id"], "kind": "prediction", "text": p["prediction"] + f" (반증 조건: {p['falsifier']}, 신뢰도 {p['confidence']})", "age_scope": None,
                      "source_ids": [], "source_title": None, "published": None, "confidence": None, "stale": False, "topic": p.get("expected_window")})
    for a in merged["design_analogues"]:
        items.append({"id": a["id"], "kind": "analogue", "text": a["idea"] + (f" 위험: {a['risk']}" if a.get("risk") else ""), "age_scope": None, "source_ids": [],
                      "source_title": None, "published": None, "confidence": None, "stale": False, "topic": ",".join(a.get("based_on_case_ids", []))})
    for t in merged["themes"]:
        items.append({"id": t["id"], "kind": "theme", "text": t["theme"] + ". " + t["summary"], "age_scope": None, "source_ids": [], "source_title": None,
                      "published": None, "confidence": None, "stale": False, "fact_ids": t["fact_ids"], "topic": t.get("strength")})
    for v in merged["voices"]:
        s_ = sid.get(v["source_id"], {})
        items.append({"id": v["id"], "kind": "voice", "text": v["text"], "age_scope": None, "source_ids": [v["source_id"]], "source_title": s_.get("title"),
                      "published": s_.get("published"), "confidence": "low", "stale": bool(s_.get("stale")), "topic": v.get("note")})
    items += extra_items or []
    ids = [i["id"] for i in items]
    dup = {k for k in ids if ids.count(k) > 1}
    if dup:
        raise ValueError(f"근거 항목 id 충돌: {sorted(dup)[:5]}")
    return items


def apply_labels(items: list[dict], labels: dict, vocab: dict) -> tuple[list[dict], dict]:
    """어휘 밖 값은 버리고 건수를 센다. 라벨이 없는 항목은 relevance=none."""
    bad, out = {}, []
    for it in items:
        lb = labels.get(it["id"], {})
        row = dict(it)
        for key, allowed in (("needs", set(vocab["needs"])), ("tags", set(vocab["tags"])), ("domains", set(vocab["domains"]))):
            keep = [x for x in lb.get(key, []) if x in allowed]
            for x in lb.get(key, []):
                if x not in allowed:
                    bad[f"{key}:{x}"] = bad.get(f"{key}:{x}", 0) + 1
            row[key] = keep
        row["relevance"] = lb.get("relevance", "none")
        out.append(row)
    return out, bad


def write_index(dir_: str, items: list[dict], vocab: dict, as_of: str):
    os.makedirs(dir_, exist_ok=True)
    json.dump({"as_of": as_of, "vocab": {"needs": sorted(vocab["needs"]), "domains": sorted(vocab["domains"])}, "items": items},
              open(os.path.join(dir_, "evidence_index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
