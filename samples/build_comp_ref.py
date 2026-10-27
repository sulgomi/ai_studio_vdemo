#!/usr/bin/env python3
"""경쟁 카드 참고자료(ui/genz-comp-ref.js) 만들기.
 - 메인 경쟁사 4곳(삼성·우리·하나·현대) 심층 조사: scenarios/genz-evidence/competitor_research/main/<key>.cards.json + .md 의 프로필 절
 - 그 밖의 젊은층 겨냥 카드 추가 조사: competitor_research/all.cards.json (메인 4곳 조사와 이름이 겹치면 뺀다)
값은 조사 기록 그대로 두고 화면에 맞는 모양으로만 옮긴다."""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CR = ROOT / "scenarios/genz-evidence/competitor_research"
ISS = [("samsung", "삼성카드"), ("woori", "우리카드"), ("hana", "하나카드"), ("hyundai", "현대카드"), ("shinhan", "신한카드(자사)")]


def section(md: str, title: str, limit=420) -> str:
    m = re.search(r"^#{2,4}\s*" + re.escape(title) + r"[^\n]*\n(.*?)(?=^#{2,4}\s|\Z)", md, re.S | re.M)
    if not m:
        return ""
    body = re.sub(r"\n{2,}", "\n", m.group(1).strip())
    body = re.sub(r"[\*`]|\[\d+(?:[,\s]*\d+)*\]", "", body)
    lines = [re.sub(r"^(?:[\-\*]\s+|\d+\.\s+)", "", l).strip() for l in body.split("\n") if l.strip() and not l.strip().startswith("|")]
    txt = " ".join(lines).replace(" - ", " · ")
    if len(txt) <= limit:
        return txt
    cut = txt[:limit]
    k = max(cut.rfind("다. "), cut.rfind("다.\n"), cut.rfind("요. "))
    return cut[:k + 2].strip() if k > limit * 0.5 else cut.rstrip() + "…"


def card_row(c):
    fee = (c.get("annual_fee_won") or {}).get("domestic") if isinstance(c.get("annual_fee_won"), dict) else None
    tiers = c.get("tiers") or []
    mins = sorted({t.get("min_prev_month_spend_won") for t in tiers if t.get("min_prev_month_spend_won") is not None})
    heads = [b.get("text") for b in (c.get("benefits") or [])[:2] if b.get("text")] or [t.get("benefit_summary") for t in tiers[:1] if t.get("benefit_summary")]
    return {"name": c.get("name"), "type": c.get("type"), "on_sale": c.get("on_sale"), "role": c.get("role"), "fee": fee,
            "mins": mins, "benefit": "; ".join(h[:110] for h in heads)[:220], "target": c.get("target_text"), "fit": c.get("genz_fit"),
            "conf": c.get("confidence"), "launched": c.get("launched"), "url": c.get("source_url")}


issuers, main_names = [], set()
for key, name in ISS:
    cp = CR / "main" / f"{key}.cards.json"
    if not cp.exists():
        continue
    cards = json.loads(cp.read_text(encoding="utf-8"))
    md = (CR / "main" / f"{key}.md").read_text(encoding="utf-8") if (CR / "main" / f"{key}.md").exists() else ""
    rows = [card_row(c) for c in cards]
    main_names |= {re.sub(r"\s+", "", c["name"] or "") for c in rows}
    issuers.append({"key": key, "name": name, "own": key == "shinhan", "n": len(rows), "on_sale": sum(1 for r in rows if r["on_sale"]),
                    "strategy": section(md, "GenZ·청년 전략"), "edge": section(md, "차별점", 300), "weak": section(md, "약점", 300), "position": section(md, "GenZ에서의 위치", 300), "cards": rows})

extra = []
ap = CR / "all.cards.json"
if ap.exists():
    for x in json.loads(ap.read_text(encoding="utf-8")):
        if re.sub(r"\s+", "", x["name"]) in main_names:
            continue
        fee = x.get("annual_fee_won") or {}
        extra.append({"name": x["name"], "issuer": x["issuer"], "type": x["type"], "on_sale": x["on_sale"], "fee": fee.get("domestic") if isinstance(fee, dict) else None,
                      "min": x.get("min_prev_month_spend_won"), "kw": x.get("target_keyword"),
                      "benefit": "; ".join(h.get("text", "") for h in (x.get("headline_benefits") or [])[:2])[:140], "fit": x.get("genz_fit"), "conf": x.get("confidence"), "url": x.get("source_url")})

out = {"as_of": "2026-10-27", "issuers": issuers, "extra": extra}
(ROOT / "ui/genz-comp-ref.js").write_text("window.COMP_REF=" + json.dumps(out, ensure_ascii=False) + ";\n", encoding="utf-8")
print("ok", [(i["name"], i["n"]) for i in issuers], "extra", len(extra))
