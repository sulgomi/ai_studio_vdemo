#!/usr/bin/env python3
"""GenZ 신용카드 E2E 시나리오의 코드 단계와 검증기.

LLM 단계(에이전트 01~10)는 agents/<폴더>/system_prompt.md 와 공통 규칙으로 따로 실행하고,
이 파일은 오케스트레이터가 코드로 하는 일만 맡는다.

  python3 harness.py validate <stage>    봉투·payload·result 스키마 + 에이전트별 코드 검사
  python3 harness.py score               기회 점수 상위 12 + 셀별 최대 도달 채택률(천장)
  python3 harness.py eval                06 컨셉 3안 평가, 승자 선정 → 06-concept/eval.json
  python3 harness.py simulate            승자 카드 가상 고객 시뮬레이션 → 07-validation/twin.json
  python3 harness.py calibrate           기준 카드(리허설 함께쌓기 카드)로 모형 수준 확인

원본 평가·시뮬레이션 코드(A live/h.js)는 이 저장소에 없다. 설계서 00 5절과 07 4절의 절차를
그대로 따라 다시 구현했고, 계수는 scenario.json 의 sim_params(PM 가정치)에 있다.
"""
import glob, json, math, os, random, re, sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
load = lambda p: json.load(open(p, encoding="utf-8"))
SC = load(f"{HERE}/scenario.json")
P = SC["sim_params"]
DB = load(f"{ROOT}/samples/03-competitor/in.sample.json")["payload"]["competitor_db"]["cards"]
ALLOWED_TAGS = load(f"{ROOT}/samples/03-competitor/in.sample.json")["payload"]["allowed_tags"]
SEG = {s["id"]: s for s in SC["segments"]}
TYPES = list(P["type_mix"])
BANNED = ["최고", "무조건", "100%", "최대", "확정", "무제한"]
PROFIT_HINT = ["번다", "불어난", "굴린", "굴려"]
CLICHE = ["다양한 혜택", "높은 할인율", "MZ 맞춤", "전월 실적 없이", "커피·OTT·편의점"]
INVEST_TAGS = {"invest_reward", "point_to_stock"}
INTERNAL = ["segId", "capPerCat", "no_cap", "minPerf", "appliedCx", "indepCx", "spend_free", "reward_cashback"]


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def tag_count():
    c = {t: 0 for t in ALLOWED_TAGS}
    for card in DB:
        for t in card["tags"]:
            c[t] = c.get(t, 0) + 1
    return c


# ---------------- 스키마 검증 ----------------

def schema_errors(stage):
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
    env_in = load(f"{ROOT}/agents/_common/envelope.in.schema.json")
    env_out = load(f"{ROOT}/agents/_common/envelope.out.schema.json")
    reg = Registry().with_resources([
        ("envelope.in.schema.json", Resource.from_contents(env_in, default_specification=DRAFT202012)),
        ("envelope.out.schema.json", Resource.from_contents(env_out, default_specification=DRAFT202012))])
    extra = []
    for f in glob.glob(f"{ROOT}/agents/[0-9][0-9]-*/*.schema.json"):
        d = load(f)
        if "$id" in d:
            extra.append((d["$id"], Resource.from_contents(d, default_specification=DRAFT202012)))
    for f in glob.glob(f"{ROOT}/agents/09-design-marketing/schema/*.schema.json"):
        extra.append(("card-studio/agents/design_marketing/schema/" + os.path.basename(f),
                      Resource.from_contents(load(f), default_specification=DRAFT202012)))
    reg = reg.with_resources(extra)
    out = []
    a_in = load(f"{ROOT}/agents/{stage}/in.schema.json")
    a_out = load(f"{ROOT}/agents/{stage}/out.schema.json")
    i = load(f"{HERE}/{stage}/in.json")
    o = load(f"{HERE}/{stage}/out.json")
    for label, schema, data in [("in", env_in, i), ("in.payload", a_in, i.get("payload", {})),
                                ("out", env_out, o), ("out.result", a_out, o.get("result"))]:
        for e in Draft202012Validator(schema, registry=reg).iter_errors(data):
            out.append({"code": "SCHEMA_INVALID", "path": label + ":" + "/".join(map(str, e.path)), "message": e.message[:200]})
    return out, i, o


def months_between(d1, d2):
    return (d2.year - d1.year) * 12 + d2.month - d1.month


def code_checks(stage, i, o):
    """설계서 요건 표 중 코드로 검사하는 것. 반려(error)와 경고(warn)를 나눠 돌려준다."""
    err, warn = [], []
    r = o.get("result") or {}
    src_ids = {s.get("id") for s in o.get("sources", [])}
    src_urls = {s.get("url") for s in o.get("sources", [])}
    today = date.fromisoformat(SC["today"])
    for f in o.get("findings", []):
        if f.get("type") == "fact" and not f.get("source_id"):
            err.append(("SOURCE_URL_UNKNOWN", f"findings/{f['id']}", "fact에 source_id 없음"))
        if f.get("source_id") and f["source_id"] not in src_ids:
            err.append(("SOURCE_URL_UNKNOWN", f"findings/{f['id']}", f"없는 출처 {f['source_id']}"))
    if stage == "02-trend":
        sig = r.get("signals", [])
        if not 4 <= len(sig) <= 6:
            err.append(("COUNT_OUT_OF_RANGE", "result/signals", f"{len(sig)}개(TR-R1)"))
        pub = {s["id"]: s.get("published") for s in o.get("sources", [])}
        for s in sig:
            for sid in s["source_ids"]:
                if sid not in src_ids and sid not in src_urls:
                    err.append(("SOURCE_URL_UNKNOWN", f"signals/{s['id']}", f"{sid}(TR-R2)"))
            dates = [pub.get(x) for x in s["source_ids"] if pub.get(x)]
            if dates and all(months_between(date.fromisoformat(d[:10]), today) > 18 for d in dates):
                warn.append(("SOURCE_STALE", f"signals/{s['id']}", "출처가 모두 18개월 초과(TR-R5)"))
    if stage == "03-competitor":
        cnt = tag_count()
        names = {c["name"] for c in DB}
        for k in ("crowded", "empty"):
            for x in r.get(k, []):
                if x["tag"] not in ALLOWED_TAGS:
                    err.append(("ENUM_UNKNOWN", f"{k}/{x['tag']}", "CP-R1"))
        for x in r.get("empty", []):
            if cnt.get(x["tag"], 0) > 8:
                err.append(("GATE_FAILED", f"empty/{x['tag']}", f"실제 {cnt[x['tag']]}종(CP-R3)"))
        for x in r.get("nearest", []):
            if x["name"] not in names:
                err.append(("ID_UNKNOWN", f"nearest/{x['name']}", "CP-R2"))
    if stage == "04-consumer":
        labels = set(i["payload"]["need_labels"])
        sigs = {s["id"] for s in i["payload"].get("trend_signals", [])}
        for n in r.get("top_needs", []):
            if n["need"] not in labels:
                err.append(("ENUM_UNKNOWN", f"top_needs/{n['need']}", "CS-R1"))
        for sid in r.get("evidence_signal_ids", []):
            if sid not in sigs:
                err.append(("ID_UNKNOWN", f"evidence_signal_ids/{sid}", "CS-R2"))
    if stage == "05-whitespace":
        ids = {f"T{n}" for n in range(1, 20)} | {f"tag:{t}" for t in ALLOWED_TAGS} | {f"need:{n}" for n in SC["need_labels"]}
        sigs = {s["id"] for s in i["payload"]["research"]["trend"]}
        picks = r.get("picks", [])
        if not any(p["seg"] == SC["scope"]["target_segment"] for p in picks):
            err.append(("GATE_FAILED", "picks", "타깃 셀 없음(WS-R2)"))
        for p in picks:
            for e in p["evidence_ids"]:
                if e not in ids or (e.startswith("T") and e not in sigs):
                    err.append(("ID_UNKNOWN", f"picks/{p['rank']}", f"{e}(WS-R4)"))
            if p["need"] == "invest":
                err.append(("GATE_FAILED", f"picks/{p['rank']}", "범위 제약: 투자 연계 제외"))
    if stage == "06-concept":
        for k, opt in enumerate(r.get("options", [])):
            for e in concept_errs(opt):
                err.append(("BANNED_WORD" if "금칙어" in e else "ENUM_UNKNOWN", f"options/{k}", e))
        levers = [x["lever"] for x in r.get("options", [])]
        if len(set(levers)) < len(levers):
            err.append(("COUNT_OUT_OF_RANGE", "options", "레버 중복(CO-R1)"))
    if stage == "07-validation":
        twin = load(f"{HERE}/07-validation/twin.json")
        if r.get("twin") != twin:
            err.append(("NUMBER_NOT_IN_INPUT", "result/twin", "twin은 코드 값 그대로여야 함"))
        allowed = {f"{v * 100:.1f}%" for v in numbers_in(twin)}
        for m in re.findall(r"\d+(?:\.\d+)?%", json.dumps(r.get("voices"), ensure_ascii=False) + r.get("summary", "")):
            if m not in allowed:
                warn.append(("NUMBER_NOT_IN_INPUT", "voices/summary", m))
        if "가상 고객 시뮬레이션(가정 기반)" not in r.get("summary", ""):
            err.append(("MISSING_DISCLOSURE", "summary", "VA-R6"))
    if stage == "08-guardrail":
        ids = [c["id"] for c in r.get("checks", [])]
        if sorted(ids) != ["G1", "G2", "G3", "G4", "G5", "G6"]:
            err.append(("COUNT_OUT_OF_RANGE", "checks", "G1~G6(GR-R1)"))
        for c in r.get("checks", []):
            for w in ["위반이다", "합법이다", "위법이다", "문제없다"]:
                if w in c.get("finding", "") + c.get("suggestion", ""):
                    err.append(("STYLE_VIOLATION", f"checks/{c['id']}", f"법률 단정 '{w}'(GR-R4)"))
    if stage == "10-plan-doc":
        md = r.get("markdown", "")
        heads = ["## 1. 요약", "## 2. 시장 조사와 기획 배경", "## 3. 신상품 컨셉과 가치 제안", "## 4. 재무 타당성과 사업 효과",
                 "## 5. 마케팅 전략 방향", "## 6. 홍보 영상 콘셉트 보드", "## 7. 추진 일정과 부서별 R&R", "## 부록"]
        pos = [md.find(h) for h in heads]
        if -1 in pos or pos != sorted(pos):
            err.append(("SECTION_MISSING", "markdown", "섹션 제목·순서(PD-R1)"))
        allowed_urls = set(i["payload"].get("allowed_urls", []))
        for u in re.findall(r"https?://[^\s)\]>\"']+", md):
            if u.rstrip(".,") not in allowed_urls:
                err.append(("SOURCE_URL_UNKNOWN", "markdown", u[:120]))
        allowed_nums = set(i["payload"].get("allowed_numbers", []))
        for m in re.findall(r"\d+(?:\.\d+)?%", md):
            if m not in allowed_nums:
                err.append(("NUMBER_NOT_IN_INPUT", "markdown", m))
        for w in INTERNAL:
            if re.search(rf"\b{w}\b", md):
                err.append(("STYLE_VIOLATION", "markdown", f"내부 필드명 {w}(PD-R10)"))
        for w in ["포트폴리오", "BEP"]:
            if w not in md:
                err.append(("MISSING_DISCLOSURE", "markdown", f"'{w}' 없음(PD-R5)"))
        if "가상 고객 시뮬레이션(가정 기반)" not in md:
            err.append(("MISSING_DISCLOSURE", "markdown", "PD-R9"))
        style = len(re.findall("—", md)) + len(re.findall(r"\*\*[^*]+:\*\*", md))
        if style >= 3:
            err.append(("STYLE_VIOLATION", "markdown", f"줄표·굵은 라벨 {style}건(PD-R11)"))
    return err, warn


def numbers_in(obj):
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from numbers_in(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from numbers_in(v)


def validate(stage):
    errs, i, o = schema_errors(stage)
    e2, warn = code_checks(stage, i, o) if not errs else ([], [])
    errs += [{"code": c, "path": p, "message": m} for c, p, m in e2]
    rep = {"stage": stage, "ok": not errs, "errors": errs, "warnings": [{"code": c, "path": p, "message": m} for c, p, m in warn]}
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    return rep


# ---------------- 기회 점수(S2) ----------------

def score():
    trend = load(f"{HERE}/02-trend/out.json")["result"]["signals"]
    cnt = tag_count()
    n = len(DB)
    rows = []
    for seg in SC["segments"]:
        for need, w in seg["need_weights"].items():
            tags = SC["need_tag_map"][need]
            crowd = sum(cnt.get(t, 0) for t in tags) / (n * len(tags))
            gap = 1 - min(1, crowd * 2.5)
            rel = [s["strength"] * s["reliability"] for s in trend if need in SC["trend_topic_need_map"].get(s["topic"], [])]
            tr = sum(rel) / len(rel) if rel else 0.15
            rows.append({"seg": seg["id"], "need": need, "score": round(w * (0.35 + 0.65 * gap) * (0.4 + 0.6 * tr), 3),
                         "parts": {"need_weight": w, "gap": round(gap, 3), "trend": round(tr, 3)}})
    rows = [r for r in rows if r["need"] != "invest"]  # 범위 제약: 투자 연계 제외
    rows.sort(key=lambda r: -r["score"])
    top = rows[:12]
    for k, r in enumerate(top, 1):
        r["rank"] = k
        r["ceiling"] = ceiling(r["seg"], r["need"])
        r["feasible"] = r["ceiling"] >= SC["scope"]["target_adopt"]
    save(f"{HERE}/_code/cells_top.json", top)
    print(json.dumps(top, ensure_ascii=False, indent=1))
    return top


def ceiling(seg_id, need):
    """셀의 최대 도달 채택률: 그 니즈를 정면으로 겨냥한 이상적 카드로 계산한 채택 의향."""
    seg = SEG[seg_id]
    top2 = sorted(seg["monthly_spend"], key=lambda c: -seg["monthly_spend"][c])[:2]
    tags = [t for t in SC["need_tag_map"][need]][:2]
    card = {"rates": {c: 0.03 for c in top2}, "capPerCat": 3, "fee": 0, "minPerf": 0, "cx": 0.2, "tags": tags}
    res = simulate_card(card, novelty=1.0, segs=[seg_id])
    return round(res["by_seg"][seg_id], 3)


# ---------------- 가상 고객 시뮬레이션(S5) ----------------

def personas(seg, rng):
    out = []
    for k in range(P["n_per_segment"]):
        t = rng.choices(TYPES, weights=[P["type_mix"][x] for x in TYPES])[0]
        spend = {c: v * math.exp(rng.gauss(0, 0.35)) for c, v in seg["monthly_spend"].items()}
        needs = {n: min(1, max(0, w + rng.gauss(0, 0.12))) for n, w in seg["need_weights"].items()}
        inertia = max(0.0, rng.gauss(P["inertia_mean"][t], P["inertia_sd"]))
        out.append({"type": t, "spend": spend, "needs": needs, "inertia": inertia, "tol": seg["complexity_tolerance"]})
    return out


def card_use(card, p, spend_mul=1.0, rate_mul=1.0):
    rates = {c: r * rate_mul for c, r in card["rates"].items()}
    spend = {c: v * spend_mul for c, v in p["spend"].items()}
    if p["type"] == "체리피커":
        used = {c: spend[c] for c in rates if c in spend}
        need = card.get("minPerf", 0) - sum(used.values())
        for c in sorted(spend, key=lambda c: -spend[c]):
            if need <= 0:
                break
            if c not in used:
                add = min(spend[c], need)
                used[c] = add
                need -= add
    else:
        share = P["card_share"][p["type"]]
        used = {c: v * share for c, v in spend.items()}
    total = sum(used.values())
    if total < card.get("minPerf", 0):
        return total, 0.0
    ben = sum(min(rates[c] * used.get(c, 0), card.get("capPerCat", 99)) for c in rates)
    return total, ben


def need_fit(card, needs):
    tags = set(card.get("tags", []))
    hit = {n for n, ts in SC["need_tag_map"].items() if tags & set(ts)}
    tot = sum(needs.values()) or 1
    return sum(w for n, w in needs.items() if n in hit) / tot


def simulate_card(card, novelty, segs=None, seed=None, spend_mul=1.0, rate_mul=1.0, nov_mul=1.0):
    rng = random.Random(P["seed"] if seed is None else seed)
    segs = segs or [s["id"] for s in SC["segments"]]
    by_seg, adopters, rejects = {}, [], {}
    for sid in [s["id"] for s in SC["segments"]]:
        pop = personas(SEG[sid], rng)  # 시드 순서를 세그먼트와 무관하게 고정
        if sid not in segs:
            continue
        n_ad = 0
        for p in pop:
            total, ben = card_use(card, p, spend_mul, rate_mul)
            value = 12 * ben - card.get("fee", 0)
            if p["type"] == "휴면 위험형":
                value = 12 * card_use(card, dict(p, type="일반형"), spend_mul, rate_mul)[1] - card.get("fee", 0)
            fit = P["need_value"] * need_fit(card, p["needs"])
            nov = P["novelty_value"] * novelty * nov_mul
            cxp = P["cx_penalty"] * max(0.0, card.get("cx", 0.3) - p["tol"] * 0.6)
            u = value + fit + nov - cxp
            if u > p["inertia"]:
                n_ad += 1
                if sid == SC["scope"]["target_segment"]:
                    prof = card.get("fee", 0) + P["revenue_rate"] * 12 * total - 12 * ben - P["operating_cost"]
                    adopters.append((p["type"], prof))
            elif sid == SC["scope"]["target_segment"]:
                reason = "complexity" if cxp > max(value, fit) else ("low_value" if value + fit + nov < p["inertia"] * 0.6 else "inertia")
                rejects[reason] = rejects.get(reason, 0) + 1
        by_seg[sid] = n_ad / len(pop)
    return {"by_seg": by_seg, "adopters": adopters, "rejects": rejects}


def static_profit(card, seg_id):
    seg = SEG[seg_id]
    p = {"type": "일반형", "spend": seg["monthly_spend"]}
    total, ben = card_use(card, p)
    return card.get("fee", 0) + P["revenue_rate"] * 12 * total - 12 * ben - P["operating_cost"]


def twin_for(card, novelty):
    tgt = SC["scope"]["target_segment"]
    base = simulate_card(card, novelty)
    ad = base["adopters"]
    by_type = {}
    for t in TYPES:
        xs = [pr for ty, pr in ad if ty == t]
        if xs:
            name = "혜택 사냥꾼(체리피커)" if t == "체리피커" else t
            by_type[name] = {"share_of_adopters": round(len(xs) / len(ad), 2), "profit": round(sum(xs) / len(xs), 2)}
    scen = [("기본", {}), ("경쟁사 모방(새로움 50%↓)", {"nov_mul": 0.5}), ("혜택 20% 축소", {"rate_mul": 0.8}), ("시장 위축", {"spend_mul": 0.85})]
    scenarios = [{"name": n, "adopt": round(simulate_card(card, novelty, **kw)["by_seg"][tgt], 3)} for n, kw in scen]
    rej = base["rejects"]
    return {
        "n_personas": P["n_per_segment"] * len(SC["segments"]),
        "seed": P["seed"],
        "target_adopt": round(base["by_seg"][tgt], 3),
        "all_segments_adopt": {SEG[s]["name"]: round(v, 3) for s, v in base["by_seg"].items()},
        "by_type": by_type,
        "adopter_profit": round(sum(x for _, x in ad) / len(ad), 2) if ad else 0.0,
        "static_profit": round(static_profit(card, tgt), 2),
        "behav_floor": P["behav_floor"],
        "scenarios": scenarios,
        "top_reject": max(rej, key=rej.get) if rej else "none",
    }


# ---------------- 컨셉 평가(S4e) ----------------

def concept_errs(opt):
    errs = []
    text = json.dumps({k: opt[k] for k in ("working_title", "one_liner", "hook", "special_point")}, ensure_ascii=False)
    for w in BANNED + PROFIT_HINT:
        if w in text:
            errs.append(f"금칙어·수익 암시 '{w}'(CO-R2)")
    for t in opt["tags"]:
        if t not in ALLOWED_TAGS:
            errs.append(f"미등록 태그 {t}(CO-R3)")
        if t in INVEST_TAGS:
            errs.append(f"범위 제약 위반: 투자 태그 {t}")
    for c, r in opt["rates"].items():
        if c not in SC["categories"]:
            errs.append(f"미등록 카테고리 {c}(CO-R4)")
        if not 0 < r <= 0.03:
            errs.append(f"혜택률 범위 {c}={r}(CO-R4)")
    if "sec" in opt.get("links", []):
        errs.append("범위 제약 위반: 증권 연계")
    cnt = tag_count()
    if not any(cnt.get(t, 0) <= 1 for t in opt["tags"]):
        errs.append("공백 태그 없음(CO-R3)")
    return errs


def special_ok(opt):
    hook = opt["special_point"]["hook"]
    stripped = hook
    for c in CLICHE:
        stripped = stripped.replace(c, "")
    if len(re.sub(r"[\s,.·]", "", stripped)) < 6:
        return False
    return all(opt["special_point"].get(k) for k in ("hook", "why_unusual", "proof_mechanism", "not_like"))


def evaluate():
    opts = load(f"{HERE}/06-concept/out.json")["result"]["options"]
    cnt = tag_count()
    tgt = SC["scope"]["target_segment"]
    rows = []
    for k, o in enumerate(opts):
        tags = set(o["tags"])
        novelty = round(sum(1 for t in tags if cnt.get(t, 0) <= 1) / len(tags), 2)
        best, nearest = 0.0, None
        for c in DB:
            j = len(tags & set(c["tags"])) / len(tags | set(c["tags"]))
            if j > best:
                best, nearest = j, c["name"]
        indep = round(min(1.0, 0.07 * len(o["mechanics"]) + 0.05 * len(o["rates"]) + (0.1 if o["minPerf"] > 0 else 0) + 0.05 * len(o.get("links", []))), 2)
        applied = o["cx"] if abs(o["cx"] - indep) <= 0.15 else round((o["cx"] + indep) / 2, 2)
        card = dict(o, cx=applied)
        sim = simulate_card(card, novelty, segs=[tgt])
        ad = sim["adopters"]
        adopt = round(sim["by_seg"][tgt], 3)
        aprof = round(sum(x for _, x in ad) / len(ad), 2) if ad else 0.0
        cherry = round(sum(1 for t, _ in ad if t == "체리피커") / len(ad), 2) if ad else 0.0
        rej = sim["rejects"]
        errs = concept_errs(o)
        sp = special_ok(o)
        prof = round(static_profit(card, tgt), 2)
        ok = (prof >= 3 and best <= 0.5 and applied <= 0.5 and sp and not errs and adopt >= SC["scope"]["target_adopt"] and aprof >= P["behav_floor"])
        fails = [m for m, bad in [("profit<3", prof < 3), ("sim>0.5", best > 0.5), ("cx>0.5", applied > 0.5),
                                   ("special_point_invalid", not sp), ("errs", bool(errs)),
                                   (f"adopt<{SC['scope']['target_adopt']}", adopt < SC["scope"]["target_adopt"]),
                                   ("adopterProfit<1.5", aprof < P["behav_floor"])] if bad]
        rows.append({"i": k, "name": o["working_title"], "profit": prof, "novelty": novelty, "sim": round(best, 2), "nearest": nearest,
                     "cx": o["cx"], "indepCx": indep, "appliedCx": applied, "adopt": adopt, "adopterProfit": aprof, "cherry": cherry,
                     "topReject": max(rej, key=rej.get) if rej else "none", "special_point_ok": sp, "errs": errs, "pass": ok, "fails": fails})
    for r in rows:
        r["score"] = round((min(r["profit"], 10) / 10 + r["novelty"] + (1 - r["sim"]) + (1 - r["appliedCx"]) + r["adopt"]) / 5, 3)
    passed = [r for r in rows if r["pass"]]
    win = max(passed, key=lambda r: r["score"]) if passed else None
    res = {"eval": rows, "winner": None if not win else {"card": opts[win["i"]], "metrics": {k: v for k, v in win.items() if k not in ("fails",)},
           "ranking": [{"i": r["i"], "name": r["name"], "score": r["score"], "pass": r["pass"]} for r in sorted(rows, key=lambda r: -r["score"])]}}
    save(f"{HERE}/06-concept/eval.json", res)
    print(json.dumps(res["eval"], ensure_ascii=False, indent=1))
    print("winner:", win and win["name"])
    return res


def simulate():
    ev = load(f"{HERE}/06-concept/eval.json")
    w = ev["winner"]
    twin = twin_for(dict(w["card"], cx=w["metrics"]["appliedCx"]), w["metrics"]["novelty"])
    save(f"{HERE}/07-validation/twin.json", twin)
    print(json.dumps(twin, ensure_ascii=False, indent=1))


def calibrate():
    ref = load(f"{ROOT}/samples/07-validation/in.sample.json")["payload"]["card"]
    ref = dict(ref, tags=[t for t in ref["tags"]])
    for sid in SEG:
        r = simulate_card(ref, 0.82, segs=[sid])
        print(sid, "adopt", round(r["by_seg"][sid], 3), "static_profit", round(static_profit(ref, sid), 2))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "validate":
        sys.exit(0 if validate(sys.argv[2])["ok"] else 1)
    {"score": score, "eval": evaluate, "simulate": simulate, "calibrate": calibrate}[cmd]()
