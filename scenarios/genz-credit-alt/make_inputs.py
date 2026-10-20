#!/usr/bin/env python3
"""H2 대안 분기(2순위 셀)의 단계별 입력(in.json)을 앞 단계 결과에서 코드로 조립한다.

  python3 make_inputs.py 07        # 06 승자 + twin.json → 07-validation/in.json
  python3 make_inputs.py 08        # 06 승자 + 07 결과 → 08-guardrail/in.json
  python3 make_inputs.py 06-rework # 08 fix 수정안 → 06-concept/in.json (재작업, 승자 안만)
  python3 make_inputs.py 09        # 확정 카드 브리프 → 09-design-marketing/in.json
형식은 기본 실행(../genz-credit/)의 입력을 그대로 따른다. 값만 이 분기의 결과로 바뀐다.
"""
import json, os, sys, copy
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "..", "genz-credit")
L = lambda p: json.load(open(os.path.join(HERE, p), encoding="utf-8"))
LB = lambda p: json.load(open(os.path.join(BASE, p), encoding="utf-8"))
def save(p, d):
    os.makedirs(os.path.dirname(os.path.join(HERE, p)), exist_ok=True)
    json.dump(d, open(os.path.join(HERE, p), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
ALT_NOTE = " H2에서 사람이 1순위(구독·디지털) 대신 2순위 셀(GenZ × 단순함)을 선택했다."


def conv(d):
    d = copy.deepcopy(d)
    if "GenZ × 단순함" not in d["conversation"]["summary"]:
        d["conversation"]["summary"] += ALT_NOTE
    return d


def head(tpl, stage, rid, question):
    d = conv(tpl)
    d["run_id"] = "genz-credit-alt-001"
    d["request_id"] = f"genz-credit-alt-001-{rid}"
    d["question"] = question
    return d


def winner():
    ev = L("06-concept/eval.json")
    return ev["winner"], ev


def stage07():
    w, ev = winner()
    twin = L("07-validation/twin.json")
    d = head(LB("07-validation/in.json"), "07", "validation-r1", f"{w['card']['working_title']}가 GenZ(만 19~29세)에게 먹힐지 가상 고객으로 보고, 유형별 반응을 알려줘.")
    p = d["payload"]
    p["card"] = w["card"]
    p["metrics"] = w["metrics"]
    p["twin"] = twin
    p["target_adopt"] = twin["target_adopt"]
    save("07-validation/in.json", d)


def stage08():
    w, ev = winner()
    twin = L("07-validation/twin.json")
    m = w["metrics"]
    d = head(LB("08-guardrail/in.json"), "08", "guardrail-r1", f"{w['card']['working_title']}를 재무와 준법 관점에서 점검해줘. 고칠 것과 법무에 확인받을 것을 나눠서.")
    p = d["payload"]
    p["card"] = w["card"]
    p["metrics"] = {k: m[k] for k in ("name", "profit", "novelty", "sim", "nearest", "adopt", "adopterProfit", "cherry", "appliedCx", "topReject") if k in m}
    p["twin"] = {k: twin[k] for k in ("target_adopt", "by_type", "adopter_profit", "static_profit", "scenarios") if k in twin}
    flags = []
    cherry = twin["by_type"].get("혜택 사냥꾼(체리피커)") or twin["by_type"].get("체리피커")
    if cherry and cherry["share_of_adopters"] >= 0.2 and cherry["profit"] < 3:
        flags.append({"check_id": "G6", "flag": f"체리피커가 채택자의 {cherry['share_of_adopters']}로 20% 이상이면서 손익 {cherry['profit']}로 3 미만"})
    p["precheck_flags"] = flags
    save("08-guardrail/in.json", d)


def stage09(benefits):
    """확정 카드 브리프 → 09 입력. benefits는 카드 rates·mechanics에서 사람이 변환한 목록(최대 6개, 형식 제한은 in.schema 참고)."""
    w, ev = winner()
    card = w["card"]
    twin = L("07-validation/twin.json")
    va = L("07-validation/out.json")["result"]
    gr = L("08-guardrail/out.json")["result"]
    d = head(LB("09-design-marketing/in.json"), "09", "design_marketing-r1", "확정된 카드 브리프로 이름 후보, 마케팅 방향, 카드 디자인 시안 3개, 영상 스토리보드(릴스·유튜브·홍보)를 만들어줘.")
    p = d["payload"]
    p["brief"] = {"text": f"GenZ(만 19~29세)를 위한 신용카드 '{card['working_title']}'의 마케팅 방향, 카드 디자인 시안, 영상 스토리보드를 만들어 주세요. {card['one_liner']}",
                  "card_type": "credit", "target": "GenZ(만 19~29세)", "card_summary": card["one_liner"], "special_point": card["special_point"],
                  "mechanics": card["mechanics"], "benefits": benefits, "working_title": card["working_title"]}
    p["guard_open_items"] = [{"id": c["id"], "item": c["item"], "status": c["status"], **({"suggestion": c["suggestion"]} if c.get("suggestion") else {})}
                             for c in gr["checks"] if c["status"] in ("fix", "needs_human")]
    p["required_disclosures"] = gr.get("required_disclosures", [])
    p["twin_facts"] = {"target_adopt": twin["target_adopt"], "by_type": twin["by_type"], "scenarios": twin["scenarios"]}
    p["voices_summary"] = va["summary"]
    save("09-design-marketing/in.json", d)


if __name__ == "__main__":
    {"07": stage07, "08": stage08}[sys.argv[1]]()
    print("ok", sys.argv[1])
