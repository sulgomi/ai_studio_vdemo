"""단일 단계 검증: python -m cardstudio.validate_cli <agent_id> <in.json> <out.json>
스키마(봉투+result) → 출처 → 에이전트별 검증(05 v2 포함). 시나리오 하네스 검증기는 따로(scenarios/<이름>/harness.py validate <단계>)."""
import json
import sys

from . import contracts, validators
from .config import AGENT_DIR


def main(argv):
    agent, fin, fout = argv
    i, o = json.load(open(fin, encoding="utf-8")), json.load(open(fout, encoding="utf-8"))
    errs = contracts.validate_envelope_in(agent, i) + contracts.validate_envelope_out(agent, o)
    if not errs:
        errs = validators.run_all(AGENT_DIR[agent], i, o, tool_urls=None)["rejects"]
    print(json.dumps({"ok": not errs, "errors": errs}, ensure_ascii=False, indent=1))
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
