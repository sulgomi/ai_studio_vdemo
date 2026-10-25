"""반박 검증 투표 집계(코드). 모델은 등급을 내고 집계와 탈락은 코드가 정한다.

  등급: 공백 후보 강3·중2·약1·폐기0, 아이디어 A3·B2·C1·X0
  렌즈 하나에 모델이 여러 개(앙상블)면 그 렌즈 등급은 중앙값(낮은 쪽), 과반이 폐기면 그 렌즈가 폐기
  어느 렌즈든 폐기면 탈락. 그 외에는 렌즈 등급의 중앙값으로 공백 후보는 유력(≥2)/후보, 아이디어는 합계로 순위
  병합: 사람이 준 merge 표 + 검증자들이 lens_fields.duplicate_of 로 가리킨 것(2표 이상)"""
from __future__ import annotations

import statistics

GRADE = {"강": 3, "중": 2, "약": 1, "폐기": 0, "A": 3, "B": 2, "C": 1, "X": 0}


def _lens_grade(grades: list[int]) -> tuple[int, bool]:
    killed = sum(1 for g in grades if g == 0) > len(grades) / 2
    s = sorted(grades)
    return s[(len(s) - 1) // 2], killed


def collect(subject_ids: list[str], checks_by_lens: dict) -> dict:
    """checks_by_lens: {lens: [checks 목록(모델 하나의 결과)...]} → {subject: {lens: {...}}}"""
    out = {sid: {} for sid in subject_ids}
    for lens, runs in checks_by_lens.items():
        for sid in subject_ids:
            rows = [c for run in runs for c in run if c["subject_id"] == sid]
            if not rows:
                continue
            g, killed = _lens_grade([GRADE[c["grade"]] for c in rows])
            out[sid][lens] = {"grade": g, "killed": killed, "votes": [c["vote"] for c in rows], "findings": [f for c in rows for f in c["findings"]][:8],
                              "corrections": [x for c in rows for x in c.get("corrections", [])],
                              "lens_fields": rows[0].get("lens_fields", {}), "all_lens_fields": [c.get("lens_fields", {}) for c in rows],
                              "confidence": [c["confidence_in_vote"] for c in rows]}
    return out


def merge_groups(explicit: dict, per_subject: dict) -> dict:
    """explicit: {대표: [병합될 id]}. duplicate_of 표시가 서로 다른 검증 2건 이상이면 추가."""
    groups = {k: list(v) for k, v in (explicit or {}).items()}
    votes = {}
    for sid, lenses in per_subject.items():
        for lens in lenses.values():
            for lf in lens["all_lens_fields"]:
                d = lf.get("duplicate_of")
                if d and d != sid:
                    votes[(sid, d)] = votes.get((sid, d), 0) + 1
    for (sid, rep), n in votes.items():
        if n >= 2 and sid not in sum(groups.values(), []) and sid not in groups:
            groups.setdefault(rep, []).append(sid)
    return groups


def tally(subjects: list[dict], checks_by_lens: dict, *, merge: dict | None = None, kind: str = "gap") -> dict:
    ids = [s["id"] for s in subjects]
    per = collect(ids, checks_by_lens)
    groups = merge_groups(merge, per)
    merged_into = {m: rep for rep, ms in groups.items() for m in ms}
    rows = []
    for s in subjects:
        lens = per[s["id"]]
        grades = {k: v["grade"] for k, v in lens.items()}
        killed = [k for k, v in lens.items() if v["killed"]]
        row = {"id": s["id"], "grades": grades, "killed_by": killed, "dropped": bool(killed), "merged_into": merged_into.get(s["id"]),
               "sum": sum(grades.values()), "median": statistics.median_low(grades.values()) if grades else 0,
               "votes": {k: v["votes"] for k, v in lens.items()}, "corrections": [x for v in lens.values() for x in v["corrections"]],
               "findings": {k: v["findings"] for k, v in lens.items()}, "lens_fields": {k: v["lens_fields"] for k, v in lens.items()}}
        if kind == "gap":
            row["tier"] = "유력(중)" if row["median"] >= 2 else "후보(약)"
        rows.append(row)
    ranked = [r for r in rows if not r["dropped"] and not r["merged_into"]]
    ranked.sort(key=lambda r: (-r["median"], -r["sum"], r["id"]) if kind == "gap" else (-r["sum"], -r["grades"].get("novelty", 0), r["id"]))
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    return {"rows": rows, "ranked": ranked, "merge_groups": groups}


def default_finalists(ranked: list[dict], by_id: dict, n: int = 8, per_theme: int = 3) -> list[str]:
    """사람이 고르기 전의 기본안: 순위 순, 같은 테마(또는 유형)는 per_theme 개까지."""
    out, count = [], {}
    for r in ranked:
        th = by_id[r["id"]].get("theme") or by_id[r["id"]].get("gap_type") or ""
        if count.get(th, 0) >= per_theme:
            continue
        count[th] = count.get(th, 0) + 1
        out.append(r["id"])
        if len(out) >= n:
            break
    return out
