"""근거 팩(scenarios/genz-evidence)을 에이전트 입력으로 잇는 검색 층.
05 시장기회와 06 CVP가 같은 사실을 같은 id(ev:<id>)로 인용하게 해서, 기회영역에서 컨셉·기획서까지 근거가 끊기지 않는다.

evidence_index.json 의 항목은 사실·트렌드·사례·제약·테마·발언이고, 각각 니즈·태그·영역(domain) 라벨을 가진다(라벨은 별도 라벨링 단계가 닫힌 어휘로 붙인다).
검색은 코드가 한다(LLM이 아니라): 라벨 겹침 점수 + 신뢰도 − 오래된 출처 감점. 같은 입력이면 같은 결과가 나온다."""
from __future__ import annotations

import json
import os

CONF = {"high": 1.0, "medium": 0.6, "low": 0.2}
YOUNG = ("20대", "Z세대", "잘파", "10대", "청년")


class EvidenceStore:
    def __init__(self, items: list[dict], cards: list[dict], sources: dict | None = None):
        self.items = {i["id"]: i for i in items}
        self.cards = cards
        self.sources = sources or {}

    @classmethod
    def load(cls, d: str) -> "EvidenceStore":
        idx = json.load(open(os.path.join(d, "evidence_index.json"), encoding="utf-8"))["items"]
        cards = json.load(open(os.path.join(d, "competitor_db.enriched.json"), encoding="utf-8"))["cards"]
        sp = os.path.join(d, "sources.json")
        srcs = {x["id"]: x for x in json.load(open(sp, encoding="utf-8"))["sources"]} if os.path.exists(sp) else {}
        return cls(idx, cards, srcs)

    def ref(self, item_id: str) -> str:
        return f"ev:{item_id}"

    def ids(self) -> set:
        return {self.ref(i) for i in self.items}

    # ---- 근거 검색 ---------------------------------------------------------------------
    def _score(self, it: dict, need, tags, domain) -> float:
        s = 0.0
        if need and need in it.get("needs", []):
            s += 3
        s += 2 * len(set(tags or []) & set(it.get("tags", [])))
        if domain and domain in it.get("domains", []):
            s += 2
        if s == 0:
            return 0.0
        if any(y in (it.get("age_scope") or "") for y in YOUNG):
            s += 1
        s += CONF.get(it.get("confidence"), 0.3)
        if it.get("stale"):
            s -= 1
        if it.get("promotional"):
            s -= 1.5       # 홍보성 출처는 수치 근거로 쓰지 않는다(SC-R7)
        return s

    def slice(self, *, need: str | None = None, mechanisms: list[str] | None = None, domain: str | None = None, k: int = 8,
              kinds: set | None = None, per_kind: int | None = None) -> list[dict]:
        scored = []
        for it in self.items.values():
            if kinds and it["kind"] not in kinds:
                continue
            sc = self._score(it, need, mechanisms, domain)
            if sc > 0:
                scored.append((-sc, it["id"], it))
        scored.sort(key=lambda x: (x[0], x[1]))
        out, per = [], {}
        for _, _, it in scored:
            if per_kind and per.get(it["kind"], 0) >= per_kind:
                continue
            per[it["kind"]] = per.get(it["kind"], 0) + 1
            out.append(self.compact(it))
            if len(out) >= k:
                break
        return out

    def compact(self, it: dict) -> dict:
        """에이전트에게 보이는 모양. 텍스트는 자르지 않는다."""
        return {"id": self.ref(it["id"]), "kind": it["kind"], "text": it["text"], "age_scope": it.get("age_scope"),
                "source": it.get("source_title"), "published": it.get("published"), "confidence": it.get("confidence"),
                "stale": bool(it.get("stale"))}

    def docs(self, pred, k_sources: int = 30, facts_per_source: int = 6) -> list[dict]:
        """근거 팩 모드(02·04): 조건(pred)에 맞는 사실을 출처별로 묶은 문서. 홍보성·낮은 신뢰도 사실은 뒤로 밀고 같은 입력이면 같은 결과."""
        rel = {"direct": 2, "indirect": 1, "none": 0}
        groups: dict = {}
        for it in self.items.values():
            if it["kind"] != "fact" or not it.get("source_ids") or not pred(it) or it.get("out_of_scope"):
                continue
            sc = rel.get(it.get("relevance"), 0) + CONF.get(it.get("confidence"), 0.3) - (1 if it.get("stale") else 0) - (2 if it.get("promotional") else 0)
            groups.setdefault(it["source_ids"][0], []).append((-sc, it["id"], it["text"]))
        ranked = sorted(groups.items(), key=lambda kv: (sum(x[0] for x in kv[1]) / len(kv[1]) - 0.01 * len(kv[1]), kv[0]))
        out = []
        for sid, facts in ranked[:k_sources]:
            src = self.sources.get(sid, {})
            if not src.get("url"):
                continue
            facts.sort()
            tier = (src.get("tier") or "B")[0]
            out.append({"id": sid, "title": src.get("title", ""), "url": src["url"], "published": src.get("published"),
                        "reliability": {"A": 0.9, "B": 0.7, "C": 0.5, "D": 0.3}.get(tier, 0.5), "tier": tier, "facts": [t for _, _, t in facts[:facts_per_source]]})
        return out

    # ---- 가장 비슷한 실제 카드 -----------------------------------------------------------
    def nearest_cards(self, tags: list[str], k: int = 4, only_on_sale: bool = False, own: bool | None = None) -> list[dict]:
        probe = set(tags)
        scored = []
        for c in self.cards:
            if only_on_sale and c.get("on_sale") is False:
                continue
            if own is not None and bool(c.get("is_own")) != own:      # own=False: 경쟁 카드만, own=True: 자사 카드만
                continue
            union = probe | set(c["tags"])
            sim = len(probe & set(c["tags"])) / len(union) if union else 0.0
            if sim > 0:
                scored.append((-sim, c["id"], c))
        scored.sort(key=lambda x: (x[0], x[1]))
        out = []
        for neg, _, c in scored[:k]:
            out.append({"id": c["id"], "name": c["name"], "official_name": c.get("official_name"), "issuer": c["issuer"], "type": c["type"],
                        "similarity": round(-neg, 2), "annual_fee_won": c.get("annual_fee_won"),
                        "min_prev_month_spend_won": c.get("min_prev_month_spend_won"), "on_sale": c.get("on_sale"),
                        "headline_benefits": (c.get("headline_benefits") or [])[:3], "explicit_target_text": c.get("explicit_target_text"),
                        "source_url": c.get("source_url"), "is_own": bool(c.get("is_own"))})
        return out
