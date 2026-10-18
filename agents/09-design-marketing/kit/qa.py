"""Automatic QA for agent output. Every check returns a list of human-readable error strings
that are sent back to the model as the tool result, so it can fix exactly those fields.

Schema validation uses `jsonschema` when installed (add it to the Lambda layer); the rule checks
below run either way.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"

try:  # optional dependency
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover
    Draft202012Validator = None

# Extend per market. Matched case-insensitively against all copy.
BANNED_BRANDS = [
    "visa", "mastercard", "master card", "amex", "american express", "unionpay", "jcb",
    "현대카드", "삼성카드", "신한카드", "국민카드", "kb국민", "롯데카드", "하나카드", "우리카드", "bc카드",
    "토스", "카카오뱅크", "카카오페이", "네이버페이", "apple", "애플페이", "삼성페이",
]
SUPERLATIVES = ["최고", "최대", "무제한", "무조건", "업계 1위", "유일"]
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
NUMBERISH = re.compile(r"\d+(\.\d+)?\s*(%|원|만원|배|퍼센트|포인트|p\b)")


def _load(name):
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


BOARDS_SCHEMA = _load("card_boards.schema.json")
STORY_SCHEMA = _load("storyboard.schema.json")
STRATEGY_SCHEMA = _load("marketing_strategy.schema.json")


def _schema_errors(doc, schema):
    if Draft202012Validator is None:
        return []
    out = []
    for e in sorted(Draft202012Validator(schema).iter_errors(doc), key=lambda e: list(e.path)):
        path = "/".join(str(p) for p in e.path) or "(root)"
        out.append(f"{path}: {e.message}")
    return out[:20]


# ---------------------------------------------------------------- color helpers
def _lum(hex_):
    r, g, b = (int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _all_copy(boards):
    c = boards.get("concept", {})
    yield c.get("tagline", ""), "concept/tagline"
    yield c.get("statement", ""), "concept/statement"
    for i, k in enumerate(c.get("keywords", [])):
        yield k, f"concept/keywords/{i}"
    for vi, v in enumerate(boards.get("variants", [])):
        s = v.get("story", {})
        yield s.get("headline", ""), f"variants/{vi}/story/headline"
        yield s.get("lead", ""), f"variants/{vi}/story/lead"
        yield s.get("persona", ""), f"variants/{vi}/story/persona"
        for pi, p in enumerate(s.get("points", [])):
            yield p.get("title", ""), f"variants/{vi}/story/points/{pi}/title"
            yield p.get("body", ""), f"variants/{vi}/story/points/{pi}/body"


def _text_rules(text, path, benefit_text):
    errs = []
    low = text.lower()
    for b in BANNED_BRANDS:
        if b in low:
            errs.append(f"{path}: mentions a real brand ('{b}'). Use only the invented brand.")
    for s in SUPERLATIVES:
        if s in text and s not in benefit_text:
            errs.append(f"{path}: '{s}' is not allowed unless it appears in the supplied benefits.")
    for m in NUMBERISH.finditer(text):
        if m.group(0) not in benefit_text:
            errs.append(f"{path}: figure '{m.group(0)}' is not from the supplied benefits. Remove it or use a placeholder.")
    if re.search(r"[\U0001F300-\U0001FAFF☀-➿]", text):
        errs.append(f"{path}: no emoji.")
    return errs


# ---------------------------------------------------------------- boards
def check_boards(boards: dict, strategy: dict | None = None) -> list[str]:
    errs = _schema_errors(boards, BOARDS_SCHEMA)
    if errs:
        return errs  # structural problems first; rule checks assume the shape

    pal = boards["palette"]
    names = {p["name"] for p in pal}
    roles = [p["role"] for p in pal]
    if roles.count("accent") != 1:
        errs.append("palette: exactly one color must have role 'accent'.")
    if roles.count("ink") != 1:
        errs.append("palette: exactly one color must have role 'ink'.")
    if "ground" not in roles:
        errs.append("palette: at least one color must have role 'ground'.")
    if not errs:
        ink = next(p["hex"] for p in pal if p["role"] == "ink")
        acc = next(p["hex"] for p in pal if p["role"] == "accent")
        for g in (p for p in pal if p["role"] == "ground"):
            if contrast(ink, g["hex"]) < 4.5:
                errs.append(f"palette: ink on ground '{g['name']}' is {contrast(ink, g['hex']):.1f}:1, needs 4.5:1.")
        if contrast(ink, acc) < 4.5:
            errs.append(f"palette: ink on accent is {contrast(ink, acc):.1f}:1; the accent must also carry ink text (4.5:1).")

    variants = boards["variants"]
    codes = [v["code"] for v in variants]
    if len(set(codes)) != 3:
        errs.append("variants: codes must be unique.")

    sigs = []
    for i, v in enumerate(variants):
        m = v["material"]
        for key in ("tint", "edge", "logo_color"):
            if key in m and m[key] not in names:
                errs.append(f"variants/{i}/material/{key}: '{m[key]}' is not a palette color name.")
        for s in m.get("stops", []):
            if s not in names:
                errs.append(f"variants/{i}/material/stops: '{s}' is not a palette color name.")
        if m["preset"] == "metal" and "base" not in m:
            errs.append(f"variants/{i}/material/base: required for preset 'metal'.")
        if m["preset"] == "gradient" and len(m.get("stops", [])) < 2:
            errs.append(f"variants/{i}/material/stops: gradient needs 2–3 palette colors.")
        sigs.append((m["preset"], m.get("tint"), m.get("base"), tuple(m.get("stops", []))))
        anchors = {p["anchor"] for p in v["story"]["points"]}
        if len(anchors) < 3:
            errs.append(f"variants/{i}/story/points: use at least 3 different anchors (now {sorted(anchors)}).")
    if len(set(sigs)) < 3:
        errs.append("variants: two variants have the same material settings. Each variant needs a different preset or clearly different params.")
    presets = [s[0] for s in sigs]
    if len(set(presets)) < 2:
        errs.append("variants: all three use the same preset. Use at least two different presets.")

    moods = [set(v["story"]["mood"]) for v in variants]
    for a in range(3):
        for b in range(a + 1, 3):
            if moods[a] & moods[b]:
                errs.append(f"variants/{a} and {b}: mood words overlap ({sorted(moods[a] & moods[b])}).")

    benefits = boards.get("benefits", [])
    btxt = " ".join(f"{b['headline']} {b['condition']}" for b in benefits)
    for text, path in _all_copy(boards):
        errs += _text_rules(text, path, btxt)
    for i, b in enumerate(benefits):
        if b.get("variant") and b["variant"] not in codes:
            errs.append(f"benefits/{i}/variant: '{b['variant']}' is not a variant code.")
    if benefits and not boards.get("needs_compliance_review"):
        errs.append("needs_compliance_review: must be true when benefits are present.")
    if strategy:
        planned = {p["variant"] for p in strategy["personas"]}
        if planned != set(codes):
            errs.append(f"variants: codes {sorted(set(codes))} differ from the strategy personas {sorted(planned)}. Use the same codes, or update_strategy first.")
    return errs


# ---------------------------------------------------------------- strategy
ASSETS = {"reels", "youtube", "promo", "boards"}


def check_strategy(st: dict, boards: dict | None = None) -> list[str]:
    errs = _schema_errors(st, STRATEGY_SCHEMA)
    if errs:
        return errs
    # copy rules: no real brands, no superlatives, no invented figures
    texts = [(st["positioning"][k], f"positioning/{k}") for k in ("statement", "for_whom", "what_it_is", "why_different")]
    texts += [(st["insight"][k], f"insight/{k}") for k in ("tension", "truth")]
    for i, p in enumerate(st["pillars"]):
        texts += [(p["message"], f"pillars/{i}/message"), (p["proof"], f"pillars/{i}/proof")]
    for i, c in enumerate(st["channels"]):
        texts.append((c["role"], f"channels/{i}/role"))
    for i, ph in enumerate(st["phases"]):
        texts += [(a, f"phases/{i}/actions/{j}") for j, a in enumerate(ph["actions"])]
    for t, path in texts:
        errs += _text_rules(t, path, "")
    # KPI targets are placeholders unless the customer gave numbers
    if not st.get("targets_from_customer"):
        for i, k in enumerate(st["kpis"]):
            t = k["target"].strip()
            if re.search(r"\d", t) and not (t.startswith("[") and t.endswith("]")):
                errs.append(f"kpis/{i}/target: '{t}' looks like an invented number. Use [목표값] unless the customer supplied it.")
    # phases: ordered, non-overlapping, and launch day 0 falls inside one of them
    ph = st["phases"]
    for i, p in enumerate(ph):
        if p["start_day"] > p["end_day"]:
            errs.append(f"phases/{i}: start_day is after end_day.")
        if i and p["start_day"] <= ph[i - 1]["end_day"]:
            errs.append(f"phases/{i}: overlaps the previous phase; phases must follow each other.")
    if not any(p["start_day"] <= 0 <= p["end_day"] for p in ph):
        errs.append("phases: launch day 0 must fall inside one phase.")
    names = {p["name"] for p in ph}
    for i, c in enumerate(st["channels"]):
        if c["phase"] not in names:
            errs.append(f"channels/{i}/phase: '{c['phase']}' is not a phase name ({sorted(names)}).")
    codes = [p["variant"] for p in st["personas"]]
    if len(set(codes)) != 3:
        errs.append("personas: each persona must pick a different variant.")
    if boards:
        bc = {v["code"] for v in boards["variants"]}
        if set(codes) != bc:
            errs.append(f"personas: variant codes {sorted(set(codes))} must match the board variants {sorted(bc)}.")
    return errs


# ---------------------------------------------------------------- storyboards
SCENE_FIT = {
    "reels": {"aspect": "9:16", "min": 12, "max": 24},
    "youtube": {"aspect": "16:9", "min": 15, "max": 45},
    "promo": {"aspect": "16:9", "min": 12, "max": 30},
}


def check_storyboard(sb: dict, boards: dict | None) -> list[str]:
    errs = _schema_errors(sb, STORY_SCHEMA)
    if errs:
        return errs
    fit = SCENE_FIT[sb["format"]]
    if sb["aspect"] != fit["aspect"] and not (sb["format"] == "reels" and sb["aspect"] == "1:1"):
        errs.append(f"aspect: {sb['format']} uses {fit['aspect']}.")
    if not fit["min"] <= sb["duration_s"] <= fit["max"]:
        errs.append(f"duration_s: {sb['format']} should be {fit['min']}–{fit['max']}s.")
    if sb["format"] == "promo" and "bpm" not in sb:
        errs.append("bpm: required for promo.")

    t = 0.0
    for i, sc in enumerate(sb["scenes"]):
        if abs(sc["start_s"] - t) > 0.05:
            errs.append(f"scenes/{i}/start_s: expected {t:.2f} (scenes must tile the timeline without gaps).")
        for j, c in enumerate(sc.get("captions", [])):
            if c["end_s"] > sc["duration_s"] + 0.01 or c["start_s"] >= c["end_s"]:
                errs.append(f"scenes/{i}/captions/{j}: times must be inside the scene (0–{sc['duration_s']}s).")
            for k in c.get("emphasis", []):
                if k >= len(c["words"]):
                    errs.append(f"scenes/{i}/captions/{j}/emphasis: index {k} out of range.")
        t = sc["start_s"] + sc["duration_s"]
    if abs(t - sb["duration_s"]) > 0.05:
        errs.append(f"scenes: they end at {t:.2f}s but duration_s is {sb['duration_s']}.")
    if sb["scenes"][-1]["preset"] != "stack_lockup":
        errs.append("scenes: the last scene must be 'stack_lockup'.")
    first_card = sb["scenes"][0]["preset"] != "heartbeat_intro" or sb["scenes"][0]["duration_s"] <= 2.0
    if not first_card:
        errs.append("scenes/0: the card must be on screen within 2 seconds.")

    if boards:
        codes = {v["code"] for v in boards["variants"]}
        if sb.get("hero_variant") and sb["hero_variant"] not in codes:
            errs.append(f"hero_variant: '{sb['hero_variant']}' is not a variant code.")
        for i, sc in enumerate(sb["scenes"]):
            if sc.get("variant") and sc["variant"] not in codes:
                errs.append(f"scenes/{i}/variant: '{sc['variant']}' is not a variant code ({sorted(codes)}).")
        btxt = " ".join(f"{b['headline']} {b['condition']}" for b in boards.get("benefits", []))
        for i, sc in enumerate(sb["scenes"]):
            for j, c in enumerate(sc.get("captions", [])):
                errs += _text_rules(" ".join(c["words"]), f"scenes/{i}/captions/{j}", btxt)
        if boards.get("benefits") and not sb.get("legal_footer"):
            errs.append("legal_footer: required when the boards carry benefits.")
    return errs


# ---------------------------------------------------------------- patches
def apply_patch(doc: dict, ops: list[dict]) -> dict:
    """ops: [{"path": "variants/1/material/tint", "value": ...}] or {"path": ..., "remove": true}.
    Returns a new document; raises ValueError with a readable message on a bad path."""
    out = copy.deepcopy(doc)
    for op in ops:
        parts = [p for p in op["path"].strip("/").split("/") if p]
        if not parts:
            raise ValueError("empty path")
        cur = out
        for p in parts[:-1]:
            cur = cur[int(p)] if isinstance(cur, list) else cur.setdefault(p, {})
        last = parts[-1]
        if isinstance(cur, list):
            idx = int(last)
            if op.get("remove"):
                cur.pop(idx)
            elif idx == len(cur):
                cur.append(op["value"])
            else:
                cur[idx] = op["value"]
        else:
            if op.get("remove"):
                cur.pop(last, None)
            else:
                cur[last] = op["value"]
    return out
