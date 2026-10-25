#!/usr/bin/env python3
"""evidence_items.json + raw/labels_*.json → evidence_index.json (런타임 EvidenceStore 입력). 어휘 밖 라벨은 버리고 보고한다."""
import json, glob, os, collections
H = os.path.dirname(os.path.abspath(__file__))
L = lambda p: json.load(open(os.path.join(H, p), encoding="utf-8"))
items = L("evidence_items.json")["items"]
sc = L("../genz-credit/scenario.json")
NEEDS = set(sc["need_labels"]) | {"control"}
DOMS = set(sc["categories"])
TAGS = set(L("../../samples/03-competitor/in.sample.json")["payload"]["allowed_tags"])
labels = {}
for f in sorted(glob.glob(os.path.join(H, "raw/labels_*.json"))):
    labels.update(json.load(open(f, encoding="utf-8"))["labels"])
missing = [i["id"] for i in items if i["id"] not in labels]
bad = collections.Counter()
out = []
for it in items:
    lb = labels.get(it["id"], {})
    needs = [n for n in lb.get("needs", []) if n in NEEDS or bad.update(["need:" + n])]
    tags = [t for t in lb.get("tags", []) if t in TAGS or bad.update(["tag:" + t])]
    doms = [d for d in lb.get("domains", []) if d in DOMS or bad.update(["domain:" + d])]
    rel = lb.get("relevance", "none")
    out.append(dict(it, needs=needs, tags=tags, domains=doms, relevance=rel))
json.dump({"as_of": "2026-10-23", "vocab": {"needs": sorted(NEEDS), "domains": sorted(DOMS)}, "items": out},
          open(os.path.join(H, "evidence_index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("items", len(out), "missing labels", missing[:5], len(missing), "invalid", dict(bad))
print("relevance", collections.Counter(i["relevance"] for i in out))
print("by need", collections.Counter(n for i in out for n in i["needs"]).most_common())
print("by domain", collections.Counter(d for i in out for d in i["domains"]).most_common())
