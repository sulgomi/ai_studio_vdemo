#!/usr/bin/env python3
"""심층 조사 결과(삼성·우리·하나·현대·신한 + 젊은층 겨냥 추가 조사)를 시나리오 경쟁 카드 DB에 합친다.
 - 기존 카드와 이름이 같으면 id 를 그대로 두고 값(연회비·실적·혜택·판매 여부·대상 문구)을 최신 조사로 보강한다.
 - 판매 종료(on_sale=false)로 확인된 카드는 DB에서 뺀다(조사 파일에는 남아 있다).
 - 신한카드 카드는 is_own=true. 이 값은 runtime 이 own_issuers 로도 다시 표시한다.
  python3 scenarios/genz-credit-v2/merge_competitors.py   (v2 와 v2-alt 의 competitor_db.json, evidence/competitor_db.enriched.json 을 같이 갱신)"""
import json, os, re, copy
H = os.path.dirname(os.path.abspath(__file__))
SC = os.path.dirname(H)
CR = os.path.join(SC, "genz-evidence", "competitor_research")
J = lambda p: json.load(open(p, encoding="utf-8"))


def norm(s):
    s = re.sub(r"[\s\-_()·.+#:/'’]+", "", (s or "").lower())
    s = re.sub(r"(체크카드|신용카드|카드|체크)$", "", s)
    return s


def won_label(v):
    if v is None:
        return None
    if v == 0:
        return "없음"
    return ("%g" % (v / 10000)) + "만원"


ISS_MAP = {"삼성": "삼성카드", "현대": "현대카드", "우리": "우리카드", "하나": "하나카드", "신한": "신한카드", "롯데": "롯데카드", "KB국민": "KB국민카드", "BC": "BC카드", "삼성카드(SC제일은행 제휴)": "삼성카드"}


def own_issuer(name):
    return (name or "") in ("신한", "신한카드")


def to_db(c, allowed, src_tag):
    fee = c.get("annual_fee_won") if isinstance(c.get("annual_fee_won"), dict) else None
    if not fee and isinstance(c.get("annual_fee"), dict):
        fee = c["annual_fee"]
    heads = []
    for b in (c.get("benefits") or [])[:4]:
        heads.append({"category": b.get("category"), "text": b.get("text"), "rate_or_amount": b.get("rate_or_amount"),
                      "condition": "; ".join(x for x in (b.get("monthly_cap") and "월 한도 %s" % b["monthly_cap"], b.get("condition")) if x) or None})
    if not heads:
        heads = [{"category": h.get("category"), "text": h.get("text"), "rate_or_amount": h.get("rate_or_amount"), "condition": h.get("condition")} for h in (c.get("headline_benefits") or [])[:4]]
    mins = [t.get("min_prev_month_spend_won") for t in (c.get("tiers") or []) if t.get("min_prev_month_spend_won") is not None]
    minp = c.get("min_prev_month_spend_won") if c.get("min_prev_month_spend_won") is not None else (min([m for m in mins if m is not None], default=None) if mins else None)
    tags = [t for t in (c.get("tags") or []) if t in allowed]
    fit = c.get("genz_fit") or "mid"
    return {"id": c["id"], "name": c["name"], "issuer": c["issuer"], "type": c["type"], "tags": tags,
            "target": "young" if fit in ("high", "mid") else "free",
            "annual_fee": won_label((fee or {}).get("domestic")) if fee else None, "is_own": own_issuer(c["issuer"]),
            "source_url": c.get("source_url"), "official_name": c.get("official_name") or c["name"], "on_sale": c.get("on_sale"),
            "annual_fee_won": fee, "min_prev_month_spend_won": minp, "headline_benefits": heads,
            "explicit_target_text": c.get("target_text") if "target_text" in c else c.get("explicit_target_text"),
            "genz_fit": fit, "genz_fit_reason": c.get("genz_fit_reason"), "source_ids": [], "as_of": "확인 2026-10-27",
            "origin": src_tag, "note": c.get("note") or "", "tag_basis": "심층 조사(공식 페이지 기준)", "tag_confidence": {"high": 0.9, "medium": 0.7, "low": 0.5}.get(c.get("confidence"), 0.7)}


def load_new():
    out = []
    for key in ("samsung", "woori", "hana", "hyundai", "shinhan"):
        p = os.path.join(CR, "main", key + ".cards.json")
        if os.path.exists(p):
            for c in J(p):
                out.append((c, "심층 조사(메인 경쟁사)" if key != "shinhan" else "심층 조사(자사)"))
    for key in ("A", "B"):
        p = os.path.join(CR, key + ".cards.json")
        if os.path.exists(p):
            for c in J(p):
                out.append((c, "추가 조사(젊은층 겨냥)"))
    return out


def merge(base):
    allowed = base["allowed_tags"]
    cards = copy.deepcopy(base["cards"])
    byname = {}
    for c in cards:
        byname[norm(c["name"])] = c
        byname[norm(c.get("official_name"))] = c
    stats = {"updated": 0, "added": 0, "dropped_off_sale": 0, "skipped_dup": 0}
    seen_new = {}
    for c, tag in load_new():
        rec = to_db(c, allowed, tag)
        key = norm(c["name"])
        if key in seen_new:       # 두 조사에 같은 카드가 있으면 뒤의 것으로 덮지 않고 건너뜀(메인 조사 우선)
            stats["skipped_dup"] += 1
            continue
        seen_new[key] = rec
        old = byname.get(key) or byname.get(norm(c.get("official_name")))
        if old is not None:
            if rec["on_sale"] is False:
                old["_drop"] = True
                stats["dropped_off_sale"] += 1
                continue
            for k in ("annual_fee", "annual_fee_won", "min_prev_month_spend_won", "headline_benefits", "explicit_target_text", "genz_fit", "genz_fit_reason", "on_sale", "source_url"):
                if rec.get(k) not in (None, [], ""):
                    old[k] = rec[k]
            old["tags"] = sorted(set(old.get("tags", [])) | set(rec["tags"]))
            old["as_of"] = rec["as_of"]
            old["note"] = ((old.get("note") or "") + " [2026-10-27 심층 조사로 보강]").strip()
            stats["updated"] += 1
        else:
            if rec["on_sale"] is False:
                stats["dropped_off_sale"] += 1
                continue
            cards.append(rec)
            stats["added"] += 1
    cards = [c for c in cards if not c.pop("_drop", False) and c.get("on_sale") is not False]
    for c in cards:
        c["issuer"] = ISS_MAP.get(c["issuer"], c["issuer"])
        c["is_own"] = own_issuer(c["issuer"])
    out = dict(base)
    out["cards"] = cards
    out["as_of"] = "2026-10-27"
    return out, stats


if __name__ == "__main__":
    base = J(os.path.join(H, "competitor_db.json"))
    if os.path.exists(os.path.join(H, "competitor_db.v1_50.json")):       # 다시 실행해도 처음 50종에서 시작한다
        base = J(os.path.join(H, "competitor_db.v1_50.json"))
    else:
        json.dump(base, open(os.path.join(H, "competitor_db.v1_50.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    db, st = merge(base)
    own = sum(1 for c in db["cards"] if c["is_own"])
    print(st, "→ 전체", len(db["cards"]), "자사", own, "경쟁", len(db["cards"]) - own)
    for d in ("genz-credit-v2", "genz-credit-v2-alt"):
        json.dump(db, open(os.path.join(SC, d, "competitor_db.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        enr = {k: v for k, v in db.items() if k != "new_tag_definitions"}
        json.dump(enr, open(os.path.join(SC, d, "evidence", "competitor_db.enriched.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
