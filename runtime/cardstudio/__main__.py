"""python -m cardstudio run --scenario genz-credit --provider replay --run-id demo-001 [--h2 1] [--human auto|cli]"""
from __future__ import annotations

import argparse
import json
import sys

from .config import Settings
from .hitl import HumanGate
from .orchestrator import Orchestrator


def main(argv=None):
    ap = argparse.ArgumentParser(prog="cardstudio")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="E2E 실행")
    r.add_argument("--scenario", default="genz-credit")
    r.add_argument("--provider", default=None, choices=["replay", "anthropic", "openai"])
    r.add_argument("--run-id", default="run-001")
    r.add_argument("--request", default="GenZ 특화 신용카드 만들어줘")
    r.add_argument("--human", default="auto", choices=["auto", "cli"])
    r.add_argument("--live-stages", default=None, help="실제 호출할 단계 접두(쉼표). 나머지는 replay. 예: 06,07,08")
    r.add_argument("--record", action="store_true", help="기록에 없는 단계에서 멈추고 입력을 내보낸다(기록 만들기). exit 3")
    r.add_argument("--h2", type=int, default=None, help="H2 에서 고를 순위 index(0=1순위). 대안 분기 재현용")
    d = sub.add_parser("discover", help="탐색 파이프라인(근거 조사 → 공백 분석 → 아이디어 → 반박 검증)")
    d.add_argument("--spec", required=True)
    d.add_argument("--run-id", default="disc-001")
    d.add_argument("--provider", default=None, choices=["replay", "anthropic", "openai"])
    d.add_argument("--human", default="auto", choices=["auto", "cli"])
    d.add_argument("--ensemble", action="append", default=[], help="에이전트=provider/model,provider/model 예: ideator=anthropic/opus,openai/opus")
    sub.add_parser("serve", help="HTTP/SSE 서버(fastapi 필요)")
    a = ap.parse_args(argv)
    if a.cmd == "serve":
        from .server import serve
        return serve()
    if a.cmd == "discover":
        from .discovery import Discovery
        st = Settings(human_mode=a.human)
        if a.provider:
            st.provider = a.provider
        for e in a.ensemble:
            k, v = e.split("=")
            st.ensembles[k] = v.split(",")
        res = Discovery(st, a.run_id, a.spec).execute()
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0
    s = Settings(scenario=a.scenario, human_mode=a.human)
    if a.provider:
        s.provider = a.provider
    over = {"H2": {"id": a.h2, "choice": a.h2, "label": f"{a.h2 + 1}순위"}} if a.h2 is not None else {}
    provider = None
    if a.live_stages:
        from .config import MVP
        from .llm import MixedProvider, make_provider
        provider = MixedProvider(make_provider(s.provider, region=s.region), make_provider("replay", f"{s.scenarios_dir}/{s.scenario}"),
                                 a.live_stages.split(","))
    s.pause_on_missing = a.record
    orch = Orchestrator(s, a.run_id, a.request, human=HumanGate(a.human, None, over), provider=provider)
    orch.human.bus = orch.run.bus
    from .llm.replay_provider import PendingStage
    try:
        res = orch.execute()
    except PendingStage as e:
        print(json.dumps({"pending_stage": e.stage, "write_to": e.path, "input": f"{orch.run.dir}/{e.stage}/in.json", "also_pending": e.also, "rotate": e.rotate, "run_dir": orch.run.dir}, ensure_ascii=False))
        return 3
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
