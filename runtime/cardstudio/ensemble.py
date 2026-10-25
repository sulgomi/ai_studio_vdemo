"""앙상블: 같은 단계를 서로 다른 모델(계열)로 돌린 결과를 합친다. 합치는 방식은 에이전트마다 다르다.
  scout / gap_analyst / ideator : 합집합(id 는 모델별 접두로 충돌 없음). 계열이 같으면 비슷한 것으로 쏠리므로 다른 계열을 권한다.
  critic                        : 합치지 않고 판정 목록을 모델 수만큼 보존(집계는 tally 가 렌즈 안에서 중앙값)
  labeler                       : 모델 과반이 붙인 라벨만 남긴다"""
from __future__ import annotations

import copy

LETTERS = "ABCDEFGH"


def variant_prefix(prefix: str, k: int) -> str:
    """id_prefix 에 변형 문자를 붙인다. 2~3자 접두는 3자까지만 허용하므로 2자 접두에만 붙는다."""
    return prefix + LETTERS[k] if len(prefix) == 2 else prefix[:2] + LETTERS[k]


def merge_results(agent: str, envs: list[dict]) -> dict:
    if len(envs) == 1:
        return envs[0]
    out = copy.deepcopy(envs[0])
    r = out["result"]
    if agent == "scout":
        for e in envs[1:]:
            for k in ("facts", "trend_items", "cases", "constraints", "predictions", "design_analogues", "gaps"):
                r[k] = r.get(k, []) + e["result"].get(k, [])
            out["sources"] += e.get("sources", [])
    elif agent == "gap_analyst":
        for e in envs[1:]:
            r["candidates"] += e["result"]["candidates"]
            r["rejected"] += e["result"].get("rejected", [])
    elif agent == "ideator":
        for e in envs[1:]:
            r["ideas"] += e["result"]["ideas"]
            r["rejected_ideas"] += e["result"].get("rejected_ideas", [])
    elif agent == "critic":
        for k, e in enumerate(envs):
            for c in e["result"]["checks"]:
                c.setdefault("lens_fields", {})["model"] = e.get("model")
        r["checks"] = [c for e in envs for c in e["result"]["checks"]]
    elif agent == "labeler":
        need = len(envs) / 2
        labels = {}
        for i in r["labels"]:
            row = {"relevance": r["labels"][i]["relevance"]}
            for key in ("needs", "tags", "domains"):
                cnt = {}
                for e in envs:
                    for x in e["result"]["labels"].get(i, {}).get(key, []):
                        cnt[x] = cnt.get(x, 0) + 1
                row[key] = sorted(x for x, n in cnt.items() if n > need)
            labels[i] = row
        r["labels"] = labels
    out["model"] = "+".join(str(e.get("model")) for e in envs)
    return out
