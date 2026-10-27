#!/usr/bin/env python3
"""시나리오 경우의 수 정리: 어느 경로(셀)에서 어떤 확인 질문까지 준비돼 있는지, 질문으로 도달 가능한 최종 제안 상태가 몇 가지인지 정리한다.
화면의 선택지에는 이 목록을 보여 주지 않는다(주소에 ?q=1 을 붙이면 리허설용으로 보인다). 결과: scenarios/시나리오_경우의수_정리.md"""
import itertools, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATHS = [("genz-credit-v2-alt", "1순위", "구독·디지털 × 이용 패턴에 맞춘 자동 배정", "킵라인"),
         ("genz-credit-v2-p2", "2순위", "절약·캐시백 × 놓친 혜택 환급", "픽백"),
         ("genz-credit-v2", "3순위", "단순함 × 졸업·실적 다시 보기(사람이 끌어올린 아이디어)", "첫단추")]
KN = {"fee": "연회비", "cap": "월 한도", "rateMul": "혜택률 배수", "minPerf": "전월실적", "add": "추가 영역"}
ORDER = ["fee", "cap", "rateMul", "minPerf", "add"]


def idx(V, k, v):
    if k == "add":
        return V["knobs"]["add"].index(v) if v in V["knobs"]["add"] else 0
    L = V["knobs"][k]
    return min(range(len(L)), key=lambda i: abs(L[i] - v))


def reachable(V, patches):
    p = V["base_key"].split("|")
    base = tuple(V["knobs_str"][k].index(p[i]) for i, k in enumerate(ORDER))
    seen, front = {base}, [base]
    pp = [{k: idx(V, k, v) for k, v in pa.items() if k in ORDER} for pa in patches]
    while front:
        nxt = []
        for st in front:
            for pa in pp:
                ns = list(st)
                for k, i in pa.items():
                    ns[ORDER.index(k)] = i
                ns = tuple(ns)
                if ns not in seen:
                    seen.add(ns)
                    nxt.append(ns)
        front = nxt
    return len(seen)


def psum(V, pa):
    return ", ".join(f"{KN[k]} {V['knobs'][k][idx(V, k, v)]}" for k, v in (pa or {}).items() if k in KN)


out = ["# 시나리오 경우의 수 정리", "", "사용자 뷰 GenZ 상세 분석 케이스에서 **어느 경로에서 어떤 확인 질문까지 준비돼 있는지**를 정리한 문서입니다. 화면의 선택지에는 이 목록을 보여 주지 않습니다(질문은 입력창에 직접 쓰고, 개발·리허설 때만 주소 뒤에 `?q=1` 을 붙이면 준비된 질문 목록이 보입니다).", ""]
sumrows, detail = [], []
tot = {"q": 0, "patch": 0, "new": 0}
for sc, rank, cell, card in PATHS:
    fu = json.loads((ROOT / "scenarios" / sc / "followups.json").read_text(encoding="utf-8"))
    V = json.loads((ROOT / "scenarios" / sc / "variants.json").read_text(encoding="utf-8"))
    allp = []
    row = {"A": [0, 0], "B": [0, 0]}
    npatch = npersona = nnew = nnotes = 0
    for cp in fu["checkpoints"]:
        for q in cp["questions"]:
            row[cp["id"]][1 if q.get("hidden") else 0] += 1
            if q.get("patch"):
                allp.append(q["patch"]); npatch += 1
            if q.get("notes"):
                nnotes += 1
            if q["answer"].get("persona"):
                npersona += 1
            nnew += sum(1 for m in q["answer"].get("added_materials", []) if m.get("origin") == "new")
    reach = reachable(V, allp)
    tot["q"] += sum(sum(v) for v in row.values()); tot["patch"] += npatch; tot["new"] += nnew
    sumrows.append(f"| {rank} | {cell} | {card} | {row['A'][0]} / {row['A'][1]} | {row['B'][0]} / {row['B'][1]} | {npatch} | {npersona} | {nnotes} | {len(V['grid'])} | {reach} |")
    detail.append((sc, rank, cell, card, fu, V))
out += ["## 1. 한눈에 보기", "", "| 경로(H2 선택) | 기회 셀 | 선정 카드 | 확인 질문 A 노출/숨김 | 확인 질문 B 노출/숨김 | 조건이 바뀌는 질문 | 페르소나 질문 | 추가 반영 사항이 붙는 질문 | 미리 계산한 조건 조합 | 질문으로 도달 가능한 최종 제안 상태 |", "|---|---|---|---|---|---|---|---|---|---|"] + sumrows
out += ["", f"- 전체 질문 {tot['q']}개(노출+숨김), 조건이 바뀌는 질문 {tot['patch']}개, 사전 작성 중 새로 찾은 외부 자료 {tot['new']}건.", "- A: 시장기회발굴 직후(기회·근거, 자사 겹침, 다른 각도, 타깃·고객, 경쟁사 비교), B: CVP기획·시장성 검증 직후(혜택 구조, 연회비·한도·조건, 고객 유형 페르소나, 수익·리스크, 경쟁사·자사 비교, 마케팅).", "- ‘도달 가능한 최종 제안 상태’는 조건이 바뀌는 질문을 어떤 순서로 몇 개든 물었을 때 만들어질 수 있는 서로 다른 카드 조건 조합의 수입니다.", ""]
out += ["## 2. 전체 흐름의 경우의 수", "",
        "1. 범위 확인(이대로 진행) → 2. 시장조사 총괄 → 3. 시장기회발굴 → **확인 질문 A(여러 번 가능) + 기회 셀 선택(3가지)** → 4. CVP기획 → 5. 시장성 검증 → **확인 질문 B(여러 번 가능)** → 6. 마케팅 → **최종 확인(이대로 확정 / 다른 CVP로 변경)** → 7. 상품기획서 작성.",
        "- 기회 셀 선택 3가지 × (A에서 한 질문 0~n개) × (B에서 한 질문 0~n개) × (최종 확인 2가지). A·B의 질문은 순서·중복에 제한이 없고, B 질문의 조건 변경은 누적됩니다.",
        "- ‘확인 질문 건너뛰기’(자동 진행)를 켜면 질문 없이 1순위 셀로 끝까지 진행합니다.",
        "- 최종 확인에서 ‘다른 CVP로 변경’을 누르면 후보 3안의 시뮬레이션 수치를 비교해 보여 주지만, 마케팅·기획서 기록이 선정안 기준이라 이 데모에서는 선정안으로 기획서를 작성합니다(화면에 그렇게 안내).",
        "- 질문 선택지는 숨겨져 있어서 사용자가 쓴 글이 준비된 질문과 맞는지가 핵심입니다: 질문의 키워드가 글에 들어 있으면 2점, 질문 문장의 단어가 들어 있으면 1점으로 가장 점수가 높은 질문을 고르고, 맞는 것이 없으면 체크포인트별 기본 답변(fallback)으로 답하며 화면에 그 사실을 밝힙니다.", ""]
out += ["## 3. 준비된 질문 전체 목록", ""]
for sc, rank, cell, card, fu, V in detail:
    out += [f"### {rank} 경로 — {card} ({cell})", ""]
    for cp in fu["checkpoints"]:
        out += [f"#### 체크포인트 {cp['id']} — {cp['title']}", "", cp["lead"], "", "| ID | 분류 | 질문 | 노출 | 조건 변경 | 추가 반영 | 영향 섹션 | 키워드 |", "|---|---|---|---|---|---|---|---|"]
        for q in cp["questions"]:
            notes = " / ".join(n["text"][:40] for n in q.get("notes", [])) or "-"
            out.append(f"| {q['id']} | {q.get('category','')} | {q['label']} | {'숨김' if q.get('hidden') else '노출'} | {psum(V, q.get('patch')) or '-'} | {notes} | {', '.join(q.get('sections', [])) or '-'} | {', '.join(q.get('keywords', []))} |")
        out.append("")
out += ["## 4. 한계", "",
        "- 준비되지 않은 질문은 가장 가까운 답이나 기본 답변으로 응답합니다. 실제 서비스에서는 질문에 맞춰 해당 단계를 다시 실행합니다.",
        "- 수치가 바뀌는 질문은 미리 계산한 조합 표에서 값을 찾습니다. 표에 없는 값(예: 연회비 2만원)은 가장 가까운 값으로 보정합니다.",
        "- 가상 고객 모형은 졸업 규칙, 월 예산 조건, 앱 기능을 반영하지 못합니다. 이 한계는 해당 답변의 ‘아직 확실하지 않은 점’에 적혀 있습니다.", ""]
(ROOT / "scenarios" / "시나리오_경우의수_정리.md").write_text("\n".join(out), encoding="utf-8")
print("ok", tot)
for r in sumrows: print(r)
