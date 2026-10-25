"""기회영역 탐색 엔진(05 시장기회의 코드 부분, v2).

기회영역 = 세그먼트 × 니즈 × 공백 혜택 방식(mechanism, 1~2개) × 혜택 영역(domain, 선택).
예전 셀은 세그먼트×니즈(예: "GenZ × 구독·디지털")라 너무 넓어서 컨셉이 붙잡을 것이 없었다. 지금은 "이 세그먼트가 중요하게
여기는데 시장이 못 채우고 있고, 채울 수 있는 구체적 방식이 비어 있는 곳"까지 좁힌다.

점수(0~1, 모두 코드 계산, 가중 기하평균이라 한 축이 바닥이면 점수도 바닥):
  중요도 I     니즈 가중치(PM 가정치)와 소비자 조사 우선순위를 섞는다
  미충족 U     니즈 전체의 혼잡 공백 + 그 방식을 쓰는 카드의 희소성
  모멘텀 M     관련 트렌드 시그널의 강도×신뢰도(오래된 출처는 반감), 시그널 수
  차별성 D     그 방식을 중심에 둔 가상 카드와 가장 비슷한 기존 카드의 유사도를 뺀 값
  영역 Q       혜택 영역(외식·온라인·구독 등)의 규모(세그먼트 월 소비 비중)와 그 영역 카드의 포화 공백
  실현성 F     채택 천장 / 목표 채택 의향(1에서 자름)
  위험 R       복잡도 허용도 초과, 규제 민감 방식 → 점수에서 감점
추가로 가중치를 ±40% 흔들어 상위 3 안에 드는 비율(rank_stability)을 구한다. 가정치에 기댄 순위가 얼마나 흔들리는지 보여 주는 값이다.
계수는 PM 가정치이며 고객 데이터로 교체 대상이다."""
from __future__ import annotations

import math
import random
from typing import Callable

WEIGHTS = {"I": 0.24, "U": 0.24, "M": 0.12, "D": 0.12, "F": 0.08, "Q": 0.10, "V": 0.10}   # V: 탐색 파이프라인의 반박 검증 결과(없으면 중립 0.5)
RISK_WEIGHT = 0.12
FLOOR = 0.05

# 방식별 고객이 느끼는 복잡도(0~1), 규제 민감도(0~1). 표에 없으면 기본값. PM 가정치.
MECH_COMPLEXITY = {"tiered_perf": .5, "group_pooling": .6, "challenge": .5, "monthly_switch": .5, "select_pack": .5, "select_item": .4,
                   "common_plus_select": .5, "benefit_rental": .6, "miss_refund": .45, "anti_cap": .3, "auto_best": .35, "ai_personalize": .45,
                   "social": .5, "count_based": .4, "time_slot": .4, "perf_recharge": .45, "life_event": .4, "paymethod_bonus": .3,
                   "subscription_ott": .25, "online_shop": .25, "simple_flat": .15, "spend_free": .15, "no_cap": .2}
MECH_REGULATORY = {"insurance_link": .4, "ai_personalize": .25, "point_to_stock": .6, "invest_reward": .6, "miss_refund": .15, "group_pooling": .2}
DEFAULT_COMPLEXITY = 0.3

# (A) 방식 후보 확장: 기본 니즈 연결(scenario.need_tag_map) 밖의 구조·조건·제휴 태그를 니즈에 추가로 잇는다. PM 가정치.
MECH_EXTRA_NEEDS = {
    "reward_flat_refund": ["saving", "simple"], "discount_counts": ["saving", "simple"], "period_bonus": ["saving"], "count_based": ["saving", "simple"],
    "time_slot": ["saving"], "life_event": ["saving", "fixed_cost"], "target_special": ["social", "saving"],
    "select_item": ["digital"], "select_pack": ["digital"], "common_plus_select": ["digital"], "monthly_switch": ["digital"], "benefit_rental": ["digital"],
    "plcc_brand": ["digital", "saving"], "bank_bundle": ["fixed_cost", "simple"], "premium_voucher": ["travel"], "esg_green": ["social"],
}
MECH_COMPLEXITY.update({"reward_flat_refund": .2, "discount_counts": .3, "period_bonus": .35, "count_based": .4, "life_event": .4, "target_special": .3,
                        "select_pack": .5, "common_plus_select": .5, "plcc_brand": .35, "bank_bundle": .4, "premium_voucher": .35, "esg_green": .3})
# 영역이 아니라 카드 형태·제한 조건이라 방식 후보에서 빼는 태그
NOT_MECHANISM = {"check_card", "txn_threshold", "tiered_perf", "dining_cafe", "delivery", "mart_daily", "fuel", "transit", "fixed_bills", "online_shop",
                 "subscription_ott", "travel_fx"}
# (B) 혜택 영역 축: 소비 카테고리 → 그 영역을 나타내는 경쟁 카드 태그
DOMAIN_TAGS = {"dining": ["dining_cafe", "delivery"], "online": ["online_shop"], "sub": ["subscription_ott"], "trans": ["transit"],
               "travel": ["travel_fx", "lounge"], "daily": ["mart_daily"], "fixed": ["fixed_bills"]}
MAX_PAIRS_FROM = 10      # 단일 방식 상위 몇 개를 짝짓기 후보로 삼을지
PAIR_PARTNERS = 4        # 각각에 붙일 짝 후보 수
OFF_TARGET_FACTOR = 0.9  # 요청 타깃 밖 세그먼트 영역의 점수 배율
MAX_OFF_TARGET = 3       # 최종 목록에 넣을 타깃 밖 영역 수 상한
DOMAINS_PER_SEG = 3      # 세그먼트별 검토할 영역 수(월 소비 상위)
EXCLUDED_BY_KEYWORD = {"투자 연계": {"needs": {"invest"}, "tags": {"invest_reward", "point_to_stock"}}}


def excluded_from_constraints(constraints: list[str]) -> tuple[set, set]:
    needs, tags = set(), set()
    for c in constraints or []:
        for kw, ex in EXCLUDED_BY_KEYWORD.items():
            if kw in c:
                needs |= ex["needs"]
                tags |= ex["tags"]
    return needs, tags


def _gm(parts: dict, weights: dict) -> float:
    return math.exp(sum(w * math.log(max(FLOOR, parts[k])) for k, w in weights.items()) / sum(weights.values()))


def mechanisms_for(sc: dict, need: str, ex_tags: set) -> list[str]:
    """(A) 니즈를 풀 수 있는 방식 후보: 시나리오의 기본 연결 + 확장 연결. 영역·카드 형태 태그는 뺀다."""
    base = [t for t in sc["need_tag_map"].get(need, [])]
    extra = [t for t, needs in MECH_EXTRA_NEEDS.items() if need in needs]
    return [t for t in dict.fromkeys(base + extra) if t not in NOT_MECHANISM and t not in ex_tags]


def find_areas(*, sc: dict, db_cards: list[dict], allowed_tags: dict, trend: list[dict], consumer: dict, tensions: list[dict],
               ceiling_fn: Callable, target_adopt: float, top: int = 12, ceiling_pool: int = 60,
               max_per_need: int = 2, max_per_mech: int = 1, max_per_domain: int = 3, ideas: list[dict] | None = None, seed_only_tags: set | None = None) -> list[dict]:
    """ceiling_fn(seg_id, tags, domains) -> 채택 천장."""
    ex_needs, ex_tags = excluded_from_constraints(sc["scope"].get("constraints", []))
    ex_tags = set(ex_tags) | set(seed_only_tags or [])   # 조사에서 나온 새 태그는 카드 DB에 0종이라 자동으로 '비어 있음'이 높게 나온다. 아이디어(시드)를 통해서만 영역이 된다
    all_cards = db_cards                       # 새로움(가장 가까운 카드와의 거리)은 자사 카드까지 포함한다: 자사와 닮으면 잠식
    db_cards = [c for c in db_cards if not c.get("is_own")]      # 혼잡·공백 집계는 경쟁 카드만
    n = len(db_cards)
    cnt = {t: 0 for t in allowed_tags}
    for c in db_cards:
        for t in c["tags"]:
            cnt[t] = cnt.get(t, 0) + 1
    prio = {x["need"]: x["priority"] for x in consumer.get("top_needs", [])}
    n_prio = max(prio.values()) if prio else 1
    target_seg = sc["scope"]["target_segment"]
    tension_text = " ".join(t["topic"] + " ".join(p.get("view", "") for p in t.get("positions", [])) for t in tensions or [])
    cats = sc.get("categories", {})

    def signals_for(need):
        ids = [topic for topic, needs in sc["trend_topic_need_map"].items() if need in needs]
        return [s for s in trend if s.get("topic") in ids]

    def domain_white(cat):
        tags = DOMAIN_TAGS.get(cat, [])
        share = sum(1 for c in db_cards if set(tags) & set(c["tags"])) / n if tags else 0.0
        return max(0.0, 1 - min(1.0, share * 2.5)), round(share, 2)

    def build(seg, need, mechs, cat, w, base_tags, sigs, need_gap, momentum, importance):
        """한 후보(방식 1~2개, 영역 0~1개)의 축 점수."""
        whites = [max(0.0, 1 - 5 * cnt.get(m, 0) / n) for m in mechs]
        if len(mechs) == 2:
            both = sum(1 for c in db_cards if set(mechs) <= set(c["tags"])) / n
            mech_white = 0.5 * (sum(whites) / 2) + 0.5 * max(0.0, 1 - 5 * both)
        else:
            mech_white = whites[0]
        unmet = 0.4 * need_gap + 0.6 * mech_white
        assumed = [m for m in mechs if m not in sc["need_tag_map"].get(need, [])]   # 확장 연결(PM 가정)로 이 니즈에 붙은 방식
        if assumed:
            unmet *= 0.9          # 비어 있는 이유가 "원하는 사람이 없어서"일 수 있고 연결 자체가 가정이라 할인
        probe = {*mechs, *base_tags[:1]}
        best, nearest = 0.0, None
        for c in all_cards:
            sim = len(probe & set(c["tags"])) / len(probe | set(c["tags"]))
            if sim > best:
                best, nearest = sim, c["name"]
        cxs = sorted((MECH_COMPLEXITY.get(m, DEFAULT_COMPLEXITY) for m in mechs), reverse=True)
        cx = cxs[0] + (0.5 * cxs[1] if len(cxs) == 2 else 0.0)       # 방식을 겹치면 복잡해진다
        risk = min(1.0, max(0.0, cx - seg["complexity_tolerance"]) * 2 + max(MECH_REGULATORY.get(m, 0.0) for m in mechs))
        if cat:
            dw, dshare = domain_white(cat)
            spend = seg["monthly_spend"]
            q = 0.5 * (spend.get(cat, 0) / max(spend.values())) + 0.5 * dw
        else:
            q, dshare = 0.35, None                                    # 영역을 정하지 않은 넓은 영역은 덜 구체적이라 낮게(구체성)
        label_hits = [allowed_tags.get(m, m) for m in mechs] + [sc["need_labels"].get(need, need)]
        return {"seg": seg["id"], "need": need, "mechs": list(mechs), "cat": cat, "risk": risk,
                "parts": {"I": importance, "U": unmet, "M": momentum, "D": 1 - best, "Q": q, "V": 0.4},   # V: 반박 검증을 거치지 않은 영역은 중립(0.5)보다 낮게
                "facts": {"cards_total": n, "cards_with_mechanism": [cnt.get(m, 0) for m in mechs], "need_gap": round(need_gap, 2),
                          "nearest_card": nearest, "nearest_sim": round(best, 2), "signal_ids": [x["id"] for x in sigs],
                          "consumer_priority": prio.get(need) if seg["id"] == target_seg else None,
                          "assumed_links": assumed, "domain_card_share": dshare, "domain_spend": seg["monthly_spend"].get(cat) if cat else None},
                "tension": any(lbl in tension_text for lbl in label_hits)}

    singles, ctx = [], {}
    for seg in sc["segments"]:
        spend = seg["monthly_spend"]
        doms = [None] + [c for c in sorted(spend, key=lambda c: -spend[c]) if c in DOMAIN_TAGS][:DOMAINS_PER_SEG]
        for need, w in seg["need_weights"].items():
            if need in ex_needs:
                continue
            tags_n = sc["need_tag_map"][need]
            crowd = sum(cnt.get(t, 0) for t in tags_n) / (n * len(tags_n))
            need_gap = 1 - min(1, crowd * 2.5)
            sigs = signals_for(need)
            strengths = sorted((x.get("strength", 0.5) * x.get("reliability", 0.5) * (0.5 if x.get("stale") else 1) for x in sigs), reverse=True)
            momentum = 0.15 if not strengths else 0.6 * (sum(strengths[:2]) / len(strengths[:2])) + 0.4 * min(1, len(strengths) / 3)
            rank_score = (n_prio + 1 - prio[need]) / n_prio if seg["id"] == target_seg and need in prio else w
            importance = 0.6 * w + 0.4 * rank_score
            sibling = [t for t in sorted(seg["need_weights"], key=lambda x: -seg["need_weights"][x]) if t != need and t not in ex_needs][:2]
            base_tags = [sc["need_tag_map"][t][0] for t in sibling]
            ctx[(seg["id"], need)] = (seg, w, base_tags, sigs, need_gap, momentum, importance)
            for mech in mechanisms_for(sc, need, ex_tags):
                for cat in doms:
                    singles.append(build(seg, need, [mech], cat, w, base_tags, sigs, need_gap, momentum, importance))

    # 탐색 파이프라인이 낸 아이디어(데모 후보)를 영역으로 올린다. 새 태그가 카드 DB에 0종이라 태그 공백도가 항상 높게 나오므로
    # 미충족(U)·차별성(D)은 태그 카운트가 아니라 '무엇이 새로운가'에 대한 참신성 검증 판정으로 정하고, 검증 등급 합이 V 축이 된다.
    NOVELTY = {"참신": 0.9, "부분 참신": 0.65, "이미 있음": 0.3}
    RISK_BY_GRADE = {3: 0.0, 2: 0.1, 1: 0.3, 0: 0.6}
    for idea in ideas or []:
        mechs = [t["key"] for t in idea.get("new_tags", [])][:2] or [m for m in idea.get("mechanisms", [])][:2]
        need = idea.get("need_key")
        if not mechs or need not in sc["need_labels"] or need in ex_needs:
            continue
        segs = [x for x in sc["segments"] if x["id"] == target_seg] or sc["segments"][:1]
        seg = segs[0]
        base = ctx.get((seg["id"], need))
        if not base:
            continue
        _, w, base_tags, sigs, need_gap, momentum, importance = base
        c = build(seg, need, mechs, idea.get("domain_key"), w, base_tags, sigs, need_gap, momentum, importance)
        nv = NOVELTY.get(idea.get("novelty_verdict"), 0.5)
        grades = idea.get("grades", {})
        c["parts"]["U"] = nv
        c["parts"]["D"] = nv
        c["parts"]["V"] = sum(grades.values()) / 9 if grades else 0.5
        c["risk"] = min(1.0, RISK_BY_GRADE.get(grades.get("risk", 2), 0.1) + max(MECH_REGULATORY.get(m, 0.0) for m in mechs))
        c["idea"] = {k: idea.get(k) for k in ("id", "name", "one_liner", "what_is_new", "nearest_cards", "concept", "evidence_ids", "risks", "open_questions", "platform_hook", "durability")}
        c["idea"]["verification"] = {"grades": grades, "novelty_verdict": idea.get("novelty_verdict"), "corrections": idea.get("corrections", [])[:6]}
        c["seed_id"] = idea["id"]
        singles.append(c)

    def pre(c):
        return _gm(c["parts"], {k: v for k, v in WEIGHTS.items() if k != "F"}) - RISK_WEIGHT * c["risk"]

    for c in singles:
        c["pre"] = pre(c)
    singles.sort(key=lambda c: -c["pre"])
    # (A) 방식 짝짓기: 상위 단일 영역의 방식에 다른 방식을 하나 겹친 후보
    pairs, seen_pair = [], set()
    for c in singles[:MAX_PAIRS_FROM * 3]:
        if len({(x["seg"], x["need"], x["mechs"][0]) for x in pairs}) >= MAX_PAIRS_FROM * PAIR_PARTNERS:
            break
        seg, w, base_tags, sigs, need_gap, momentum, importance = ctx[(c["seg"], c["need"])]
        partners = [p for p in singles if p["seg"] == c["seg"] and p["cat"] == c["cat"] and p["mechs"][0] != c["mechs"][0]
                    and p["need"] != c["need"] or (p["seg"] == c["seg"] and p["need"] == c["need"] and p["cat"] == c["cat"] and p["mechs"][0] != c["mechs"][0])]
        added = 0
        for p in partners:
            key = (c["seg"], c["need"], c["cat"], tuple(sorted([c["mechs"][0], p["mechs"][0]])))
            if key in seen_pair:
                continue
            seen_pair.add(key)
            d = build(seg, c["need"], [c["mechs"][0], p["mechs"][0]], c["cat"], w, base_tags, sigs, need_gap, momentum, importance)
            d["pre"] = pre(d)
            pairs.append(d)
            added += 1
            if added >= PAIR_PARTNERS:
                break
    cand = sorted(singles + pairs, key=lambda c: -c["pre"])
    # (seg, need, 방식 조합)마다 영역 변형 최대 2개만, 천장 계산 비용이 있으므로 풀을 제한
    # 천장 계산 대상: 니즈별로 돌아가며(라운드로빈) 좋은 후보부터 담아, 한 니즈가 풀을 독점하지 않게 한다.
    # (seg, need, 방식 조합)마다 영역 변형은 1개씩, 자리가 남으면 2·3번째 변형(영역이 한쪽으로 몰릴 때 다른 영역 후보가 남도록).
    by_need: dict = {}
    for c in cand:
        by_need.setdefault(c["need"], []).append(c)
    pool, per = [c for c in cand if c.get("seed_id")], {}      # 시드는 풀 크기와 상관없이 항상 평가한다
    for limit in (1, 2, 3):
        idx = {nd: 0 for nd in by_need}
        progressed = True
        while progressed and len(pool) < ceiling_pool:
            progressed = False
            for nd, lst in by_need.items():
                while idx[nd] < len(lst):
                    c = lst[idx[nd]]
                    idx[nd] += 1
                    k = (c["seg"], c["need"], tuple(c["mechs"]))
                    if per.get(k, 0) >= limit or c in pool:
                        continue
                    per[k] = per.get(k, 0) + 1
                    pool.append(c)
                    progressed = True
                    break
                if len(pool) >= ceiling_pool:
                    break
        if len(pool) >= ceiling_pool:
            break
    cache: dict = {}

    def evaluate(c):
        domains = [c["cat"]] if c["cat"] else []
        key = (c["seg"], tuple(sorted(c["mechs"])), tuple(domains))
        if key not in cache:
            cache[key] = ceiling_fn(c["seg"], list(c["mechs"]), domains)
        c["ceiling"] = cache[key]
        c["parts"]["F"] = min(1.0, c["ceiling"] / target_adopt) if target_adopt else 1.0
        c["score"] = _gm(c["parts"], WEIGHTS) - RISK_WEIGHT * c["risk"]
        if c["seg"] != target_seg:
            c["score"] *= OFF_TARGET_FACTOR      # 요청 타깃이 아닌 세그먼트는 감점(참고용 인접 영역)

    for c in pool:
        evaluate(c)

    def select(pool):
        picked, per_need, per_mech, per_dom, blocked, off = [], {}, {}, {}, [], 0
        for c in sorted(pool, key=lambda c: -c["score"]):
            if c["seg"] != target_seg and off >= MAX_OFF_TARGET:
                continue
            mk = (c["need"], tuple(c["mechs"]))   # 같은 니즈·방식은 세그먼트가 달라도 한 번만(하위 세그먼트 중복 방지)
            if per_need.get(c["need"], 0) >= max_per_need or per_mech.get(mk, 0) >= max_per_mech:
                continue
            if c["cat"] and per_dom.get(c["cat"], 0) >= max_per_domain:
                blocked.append(c)
                continue
            per_need[c["need"]] = per_need.get(c["need"], 0) + 1
            per_mech[mk] = per_mech.get(mk, 0) + 1
            if c["cat"]:
                per_dom[c["cat"]] = per_dom.get(c["cat"], 0) + 1
            picked.append(c)
            off += c["seg"] != target_seg
        return picked, blocked, {d for d, k in per_dom.items() if k >= max_per_domain}

    # 한 영역(예: 온라인)이 상위를 독식하면, 막힌 조합의 다음 영역 변형을 평가해 풀에 넣고 다시 고른다
    for _ in range(4):
        picked, blocked, saturated = select(pool)
        if len(picked) >= top or not blocked:
            break
        added = 0
        for c in blocked[:12]:
            k = (c["seg"], c["need"], tuple(c["mechs"]))
            alts = [x for x in cand if (x["seg"], x["need"], tuple(x["mechs"])) == k and x["cat"] not in saturated and x not in pool]
            if alts:
                pool.append(alts[0])
                evaluate(alts[0])
                added += 1
        if not added:
            break
    picked, _, _ = select(pool)
    pool.sort(key=lambda c: -c["score"])
    # 탐색 파이프라인이 검증해서 올린 후보(시드)는 PM이 확정한 데모 후보라 목록에서 빠지지 않게 한다(니즈·방식 상한 적용 안 함).
    # 자리가 모자라면 시드가 아닌 영역 중 점수가 가장 낮은 것부터 뺀다.
    for c in pool:
        if c.get("seed_id") and c not in picked:
            picked.append(c)
    picked.sort(key=lambda c: -c["score"])
    while len(picked) > top:
        idx = max((i for i, c in enumerate(picked) if not c.get("seed_id")), default=None)
        if idx is None:
            break
        picked.pop(idx)
    picked = picked[:max(top, sum(1 for c in picked if c.get("seed_id")))]
    stability = _stability(pool, picked)
    out = []
    for k, c in enumerate(picked, 1):
        p = {key: round(v, 3) for key, v in c["parts"].items()}
        p["R"] = round(c["risk"], 3)
        sig_n = len(c["facts"]["signal_ids"])
        ev = sig_n + (1 if c["facts"]["consumer_priority"] and c["facts"]["consumer_priority"] <= 3 else 0)
        conf = "high" if ev >= 3 and stability[id(c)] >= 0.6 else "medium" if ev >= 2 else "low"
        kind = ("미충족 핵심" if p["I"] >= 0.75 and p["U"] >= 0.7 else "흐름 편승" if p["M"] >= 0.45 and p["U"] >= 0.5
                else "차별 틈새" if p["D"] >= 0.75 and p["I"] < 0.75 else "보조 후보")
        aid = f"IDEA-{c['seed_id']}" if c.get("seed_id") else f"A-{c['seg']}-{c['need']}-{'+'.join(c['mechs'])}" + (f"-{c['cat']}" if c["cat"] else "")
        ev_ids = c["facts"]["signal_ids"] + [f"tag:{m}" for m in c["mechs"]] + [f"need:{c['need']}"] + [f"tag:{t}" for t in DOMAIN_TAGS.get(c["cat"], [])[:1]]
        out.append({"id": aid, "seg": c["seg"], "need": c["need"], "mechanisms": c["mechs"], "domain": c["cat"],
                    "domain_label": cats.get(c["cat"]) if c["cat"] else None,
                    "score": round(c["score"], 3), "rank": k, "ceiling": c["ceiling"], "feasible": c["ceiling"] >= target_adopt,
                    "type": kind, "confidence": conf, "rank_stability": round(stability[id(c)], 2), "parts": p, "facts": c["facts"],
                    "tension": c["tension"], "assumption_dependent": True, "evidence_ids": ev_ids,
                    **({"idea": c["idea"]} if c.get("idea") else {})})
    return out


def _stability(pool: list[dict], picked: list[dict], n_samples: int = 40, seed: int = 7) -> dict:
    """가중치를 ±40% 흔들었을 때 상위 3에 드는 비율."""
    rng = random.Random(seed)
    hits = {id(c): 0 for c in picked}
    for _ in range(n_samples):
        w = {k: v * rng.uniform(0.6, 1.4) for k, v in WEIGHTS.items()}
        ranked = sorted((c for c in pool if "F" in c["parts"]), key=lambda c: -(_gm(c["parts"], w) - RISK_WEIGHT * c["risk"]))
        # 니즈 상한을 같은 방식으로 적용
        seen, seen_m, top3 = {}, set(), []
        for c in ranked:
            mk = (c["need"], tuple(c["mechs"]))
            if seen.get(c["need"], 0) >= 2 or mk in seen_m:
                continue
            seen[c["need"]] = seen.get(c["need"], 0) + 1
            seen_m.add(mk)
            top3.append(c)
            if len(top3) == 3:
                break
        for c in top3:
            if id(c) in hits:
                hits[id(c)] += 1
    return {k: v / n_samples for k, v in hits.items()}
