"""출력 검증 4~5단계(00 설계서 6-4): 출처 대조 → 금칙어·준법 → 에이전트별 검증기.
스키마 검증(1~2단계)은 contracts 가 한다. 에이전트별 검증기는 시나리오 하네스(code_checks)를 플러그인으로 받는다."""
from __future__ import annotations

import json
import re

BANNED = ["최고", "무조건", "100%", "최대", "확정", "무제한"]
PROFIT_HINT = ["번다", "불어난", "굴린", "굴려"]


def check_sources(out: dict, tool_urls: set | None) -> tuple[list, list]:
    """SRC-1: fact 는 sources id 를 가리킨다. SRC-2: (live 에서) sources URL 은 이번 호출 도구 결과에 있어야 한다."""
    errs, warns = [], []
    ids = {s.get("id") for s in out.get("sources", [])}
    for f in out.get("findings", []):
        if f.get("type") == "fact" and not f.get("source_id"):
            errs.append(("SOURCE_URL_UNKNOWN", f"findings/{f.get('id')}", "fact 에 source_id 없음"))
        elif f.get("source_id") and f["source_id"] not in ids:
            errs.append(("SOURCE_URL_UNKNOWN", f"findings/{f.get('id')}", f"없는 출처 {f['source_id']}"))
    if tool_urls is not None:
        for s in out.get("sources", []):
            if s.get("url") and s["url"] not in tool_urls and not s["url"].startswith("https://card-studio.invalid"):
                errs.append(("SOURCE_URL_UNKNOWN", f"sources/{s.get('id')}", "이번 호출의 도구 결과에 없는 URL(SRC-2)"))
    return errs, warns


def check_copy(texts: list[tuple[str, str]]) -> list:
    """광고성 문구 필드(path, text)에 금칙어·수익 암시 표현이 있으면 반려. 어떤 필드가 문구인지는 에이전트별 검증기가 넘긴다."""
    errs = []
    for path, t in texts:
        for w in BANNED + PROFIT_HINT:
            if w in t:
                errs.append(("BANNED_WORD", path, f"'{w}'"))
    return errs


CONF_ORDER = {"low": 0, "medium": 1, "high": 2}


def check_whitespace_v2(env_in: dict, env_out: dict) -> list:
    """05 시장기회 v2(기회영역) 요건 WS-R8~R12. cells_top 항목에 id 가 있을 때만 적용(구형 셀 입력은 건너뜀)."""
    cells = {c["id"]: c for c in env_in["payload"].get("cells_top", []) if c.get("id")}
    if not cells:
        return []
    errs, picks = [], env_out["result"].get("picks", [])
    blob = json.dumps(env_in["payload"], ensure_ascii=False)
    for p in picks:
        at = f"picks/{p.get('rank')}"
        for f in ("statement", "mechanisms", "unmet_gap", "why_now", "hypotheses_to_validate", "kill_criteria"):
            if not p.get(f):
                errs.append(("SECTION_MISSING", f"{at}/{f}", "기회영역 설명 필드 누락(WS-R8)"))
        a = cells.get(p.get("area_id"))
        if p.get("area_id") and not a:
            errs.append(("ID_UNKNOWN", f"{at}/area_id", f"{p['area_id']}(WS-R8)"))
        elif a:
            if (a["seg"], a["need"]) != (p["seg"], p["need"]):
                errs.append(("ID_UNKNOWN", at, "area_id 의 seg·need 와 다름(WS-R10)"))
            if p.get("domain") != a.get("domain"):
                errs.append(("ID_UNKNOWN", f"{at}/domain", "영역의 혜택 영역(domain)과 다름(WS-R14)"))
            if not set(p.get("mechanisms", [])) <= set(a.get("mechanisms", [])):
                errs.append(("ENUM_UNKNOWN", f"{at}/mechanisms", "영역에 없는 방식(WS-R9)"))
            if p.get("confidence") and CONF_ORDER[p["confidence"]] > CONF_ORDER[a["confidence"]]:
                errs.append(("GATE_FAILED", f"{at}/confidence", f"코드 신뢰도 {a['confidence']}보다 높게 쓸 수 없다(WS-R12)"))
        elif p.get("origin") != "tension":
            errs.append(("ID_UNKNOWN", f"{at}/area_id", "area_id 없이 고르려면 origin=tension(WS-R8)"))
        text = " ".join(str(p.get(f, "")) for f in ("statement", "unmet_gap", "why_now", "kill_criteria", "rationale", "risk"))
        for m in re.findall(r"\d+(?:\.\d+)?%", text):
            if m not in blob and m.rstrip("%") not in blob:
                errs.append(("NUMBER_NOT_IN_INPUT", at, m))
    ev_ids = {e["id"] for e in env_in["payload"].get("evidence", [])}
    if ev_ids:
        for p in picks:
            cited = [x for x in p.get("evidence_ids", []) if x.startswith("ev:")]
            if not cited:
                errs.append(("SECTION_MISSING", f"picks/{p.get('rank')}/evidence_ids", "입력 evidence가 있는데 ev: 근거를 하나도 인용하지 않음(WS-R15)"))
            for x in cited:
                if x not in ev_ids:
                    errs.append(("ID_UNKNOWN", f"picks/{p.get('rank')}/evidence_ids", f"{x}(WS-R15)"))
    if env_in["payload"].get("pm_directions") and any(str(c).startswith("IDEA-") for c in cells) and not any(str(p.get("area_id") or "").startswith("IDEA-") for p in picks):
        errs.append(("GATE_FAILED", "picks", "pm_directions 가 있는데 컨셉 아이디어(IDEA-) 영역이 하나도 없음(WS-R16)"))
    if len(picks) >= 3 and len({p["need"] for p in picks}) < 2:
        errs.append(("COUNT_OUT_OF_RANGE", "picks", "세 영역이 모두 같은 니즈(WS-R11 다양성)"))
    return errs


def check_concept_v2(env_in: dict, env_out: dict) -> list:
    """06 CVP 근거 연결 요건 CO-R12~R14. payload 에 evidence 또는 competitor_refs 가 있을 때만 적용."""
    pl = env_in["payload"]
    ev_ids = {e["id"] for e in pl.get("evidence", [])}
    cards = pl.get("competitor_refs", []) + pl.get("own_refs", [])      # 대안은 경쟁 카드 또는 자사 카드(잠식 대상)
    if not ev_ids and not cards:
        return []
    errs = []
    names = [n for c in cards for n in (c.get("name"), c.get("official_name")) if n]
    for k, o in enumerate(env_out["result"].get("options", [])):
        at = f"options/{k}"
        cvp = o.get("cvp", {})
        rtb = cvp.get("reason_to_believe", "")
        cited = set(re.findall(r"ev:[A-Za-z0-9_]+", rtb)) | {x for x in o.get("evidence_ids", []) if x.startswith("ev:")}
        for x in cited:
            if x not in ev_ids:
                errs.append(("ID_UNKNOWN", f"{at}/evidence", f"{x}(CO-R6)"))
        if not re.search(r"ev:|T[0-9]+|tag:|need:|가정", rtb):
            errs.append(("ID_UNKNOWN", f"{at}/cvp/reason_to_believe", "근거 id 도 '가정' 도 없음(CO-R6)"))
        if ev_ids and not any(x.startswith("ev:") for x in re.findall(r"ev:[A-Za-z0-9_]+", rtb)) and "가정" not in rtb:
            errs.append(("ID_UNKNOWN", f"{at}/cvp/reason_to_believe", "입력 evidence 를 인용하거나 '가정'이라고 써야 함(CO-R6)"))
        if names and not any(n in cvp.get("alternative", "") for n in names):
            errs.append(("ID_UNKNOWN", f"{at}/cvp/alternative", "대안은 competitor_refs 의 실제 카드 이름이어야 함(CO-R12)"))
        if o.get("links"):
            if not pl.get("invest_rules"):
                errs.append(("GATE_FAILED", f"{at}/links", "invest_rules 가 비어 있어 투자·보험·은행 연계는 범위 밖(CO-R13)"))
            if "sec" in o["links"] and "원금 손실" not in " ".join(o.get("mechanics", [])):
                errs.append(("MISSING_DISCLOSURE", f"{at}/mechanics", "증권 연계에 원금 손실 고지 문장 없음(CO-R8)"))
    return errs


# ---- 탐색 파이프라인(11~15) 검증기 ---------------------------------------------------------------
def _norm(i: str) -> str:
    return i[3:] if isinstance(i, str) and i.startswith("ev:") else i


def check_discovery(agent_dir: str, env_in: dict, env_out: dict, fetched: dict | None = None) -> list:
    """11 scout(SC), 12 gap_analyst(GA), 13 ideator(ID), 14 critic(CR), 15 labeler(LB) 요건. fetched: {url: 본문} (live 에서 quote 대조용)."""
    pl, r = env_in["payload"], env_out["result"]
    errs = []
    if agent_dir == "11-scout":
        srcs = {s["id"]: s for s in env_out.get("sources", [])}
        fact_ids = {f["id"] for f in r.get("facts", [])}
        known_urls = set(pl.get("known_source_urls", []))
        for f in r.get("facts", []):
            if f["source_id"] not in srcs:
                errs.append(("SOURCE_URL_UNKNOWN", f"facts/{f['id']}", f"없는 출처 {f['source_id']}(SC-R1)"))
            if fetched is not None and f.get("quote_verified") and f.get("quote"):
                text = fetched.get(srcs.get(f["source_id"], {}).get("url"), "")
                if text and re.sub(r"\s+", "", f["quote"]) not in re.sub(r"\s+", "", text):
                    errs.append(("NUMBER_NOT_IN_INPUT", f"facts/{f['id']}/quote", "quote_verified=true 인데 받은 본문에 없음(SC-R2)"))
        for t in r.get("trend_items", []):
            for x in t["fact_ids"]:
                if x not in fact_ids:
                    errs.append(("ID_UNKNOWN", f"trend_items/{t['id']}", f"{x}(SC-R5)"))
        tids = {t["id"] for t in r.get("trend_items", [])}
        for p_ in r.get("predictions", []):
            for x in p_["based_on_trend_item_ids"]:
                if x not in tids:
                    errs.append(("ID_UNKNOWN", f"predictions/{p_['id']}", f"{x}(SC-R5)"))
        for c in r.get("cases", []):
            for x in c["source_ids"]:
                if x not in srcs:
                    errs.append(("SOURCE_URL_UNKNOWN", f"cases/{c['id']}", f"{x}(SC-R5)"))
        for sid_, s_ in srcs.items():
            if s_.get("url") in known_urls:
                errs.append(("SOURCE_URL_UNKNOWN", f"sources/{sid_}", "known_source_urls 의 출처를 다시 씀(SC-R8)"))
    elif agent_dir == "12-gap-analyst":
        ev = {_norm(e["id"]) for e in pl["evidence"]} | {_norm(i) for i in pl.get("all_evidence_ids", [])}
        names = {c["name"] for c in pl["competitor_cards"]}
        lo, hi = (pl.get("n_candidates") or {}).get("min", 4), (pl.get("n_candidates") or {}).get("max", 7)
        if not lo <= len(r["candidates"]) <= hi:
            errs.append(("COUNT_OUT_OF_RANGE", "candidates", f"{len(r['candidates'])}개(GA-R1)"))
        for c in r["candidates"]:
            at = f"candidates/{c['id']}"
            for b in c["genz_basis"]:
                if _norm(b["fact_id"]) not in ev:
                    errs.append(("ID_UNKNOWN", f"{at}/genz_basis", f"{b['fact_id']}(GA-R2)"))
            cmp_ = c["existing_check"]["db_cards_compared"]
            if len(cmp_) < 3:
                errs.append(("COUNT_OUT_OF_RANGE", f"{at}/existing_check", "대조한 카드가 3개 미만(GA-R3)"))
            for n in cmp_:
                if n not in names:
                    errs.append(("ID_UNKNOWN", f"{at}/existing_check", f"카드 '{n}'(GA-R3)"))
            for t in c["mechanism_tags"]:
                if t not in pl["allowed_tags"]:
                    errs.append(("ENUM_UNKNOWN", f"{at}/mechanism_tags", f"{t}(GA-R4)"))
            if c["need_key"] not in pl["need_labels"]:
                errs.append(("ENUM_UNKNOWN", f"{at}/need_key", f"{c['need_key']}(GA-R5)"))
    elif agent_dir == "13-ideator":
        ev = {_norm(e["id"]) for e in pl["evidence"]} | {_norm(g["id"]) for g in pl.get("gap_candidates", [])} | {_norm(i) for i in pl.get("all_evidence_ids", [])}
        names = {c["name"] for c in pl["competitor_cards"]}
        lo, hi = (pl.get("n_ideas") or {}).get("min", 6), (pl.get("n_ideas") or {}).get("max", 9)
        if not lo <= len(r["ideas"]) <= hi:
            errs.append(("COUNT_OUT_OF_RANGE", "ideas", f"{len(r['ideas'])}개(ID-R1)"))
        for i in r["ideas"]:
            at = f"ideas/{i['id']}"
            for n in i["nearest_cards"]:
                if n["card"] not in names:
                    errs.append(("ID_UNKNOWN", f"{at}/nearest_cards", f"카드 '{n['card']}'(ID-R2)"))
            for x in i["evidence_ids"]:
                if _norm(x) not in ev:
                    errs.append(("ID_UNKNOWN", f"{at}/evidence_ids", f"{x}(ID-R3)"))
            for t in i.get("new_tags", []):
                if t["key"] in pl["allowed_tags"]:
                    errs.append(("ENUM_UNKNOWN", f"{at}/new_tags", f"{t['key']} 는 이미 있는 태그(ID-R5)"))
            text = json.dumps({k: i.get(k) for k in ("name", "one_liner")}, ensure_ascii=False)   # 컨셉 안의 '최대 N원' 같은 서술은 06 컨셉 단계가 다시 검사한다
            for w in BANNED + PROFIT_HINT:
                if w in text:
                    errs.append(("BANNED_WORD", at, f"'{w}'(ID-R6)"))
    elif agent_dir == "14-critic":
        subj = {s["id"] for s in pl["subjects"]}
        got = [c["subject_id"] for c in r["checks"]]
        if set(got) != subj:
            errs.append(("COUNT_OUT_OF_RANGE", "checks", f"판정 누락 {sorted(subj - set(got))[:5]} 또는 모르는 대상 {sorted(set(got) - subj)[:5]}(CR-R1)"))
        bad_g, dead_g = {"폐기", "X", "약", "C"}, {"폐기", "X"}
        need = {"existing": ["closest_real_card"], "novelty": ["closest_real_card", "novelty_verdict"], "evidence": ["demand_evidence"], "risk": ["blocking", "must_check_first"]}
        for c in r["checks"]:
            at = f"checks/{c['subject_id']}"
            if (c["vote"] == "refute" and c["grade"] not in bad_g) or (c["vote"] == "confirm" and c["grade"] in dead_g):
                errs.append(("SCHEMA_INVALID", at, f"vote={c['vote']} 와 grade={c['grade']} 가 어긋남(CR-R2)"))
            for k in (need[pl["lens"]["id"]] if pl["subject_kind"] == "idea" else []):   # CR-R4: 아이디어는 필수, 공백 후보는 선택
                if k not in c.get("lens_fields", {}):
                    errs.append(("SCHEMA_INVALID", f"{at}/lens_fields", f"{k} 없음(CR-R4)"))
            if pl["lens"]["id"] == "existing" and not r.get("search_available", True) and c["vote"] != "refute" and c["confidence_in_vote"] == "high":
                errs.append(("GATE_FAILED", at, "검색 불가인데 확신 high(CR-R5)"))
    elif agent_dir == "15-labeler":
        v = pl["vocab"]
        ids = {i["id"] for i in pl["items"]}
        if set(r["labels"]) != ids:
            errs.append(("COUNT_OUT_OF_RANGE", "labels", f"누락 {sorted(ids - set(r['labels']))[:5]}(LB-R1)"))
        for k, lb in r["labels"].items():
            for key, vocab in (("needs", v["needs"]), ("tags", v["tags"]), ("domains", v["domains"])):
                for x in lb.get(key, []):
                    if x not in vocab:
                        errs.append(("ENUM_UNKNOWN", f"labels/{k}/{key}", f"{x}(LB-R2)"))
    return errs


def run_all(agent_dir: str, env_in: dict, env_out: dict, *, tool_urls: set | None, legacy=None, fetched: dict | None = None) -> dict:
    errs, warns = check_sources(env_out, tool_urls)
    if legacy is not None and not errs:
        e2, w2 = legacy.code_checks(agent_dir, env_in, env_out)
        errs += e2
        warns += w2
    if agent_dir == "05-whitespace" and not errs:
        errs += check_whitespace_v2(env_in, env_out)
    if agent_dir == "06-concept" and not errs:
        errs += check_concept_v2(env_in, env_out)
    if agent_dir in ("11-scout", "12-gap-analyst", "13-ideator", "14-critic", "15-labeler") and not errs:
        errs += check_discovery(agent_dir, env_in, env_out, fetched)
    rej = [{"code": c, "path": p, "message": m} for c, p, m in errs]
    return {"passed": not rej, "warnings": [{"code": c, "path": p, "message": m} for c, p, m in warns], "rejects": rej}
