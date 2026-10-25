"""HTTP/SSE 서버(UI 연결용). fastapi + uvicorn 필요: pip install -r runtime/requirements.txt
  POST /runs                      {scenario?, request?, h2?}  → {run_id}  (백그라운드 실행)
  GET  /runs/{id}/events          SSE. 이벤트 이름 = trace event(run_start, call, validate, human_wait …)
  POST /runs/{id}/human/{point}   {decision}                  → 대기 중인 H1~H5 에 결정 전달
  GET  /runs/{id}/result          완료 후 final/summary.json
UI(ui/user-view.html)는 지금 저장된 기록을 재생한다. 이 스트림을 구독하도록 바꾸면 같은 화면이 실제 실행을 보여 준다."""
from __future__ import annotations

import asyncio
import json
import os
import threading
import uuid

from .config import Settings
from .hitl import HumanGate
from .orchestrator import Orchestrator

RUNS: dict[str, Orchestrator] = {}


def make_app():
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import StreamingResponse
    app = FastAPI(title="card-studio")

    @app.post("/runs")
    def start(body: dict | None = None):
        body = body or {}
        rid = "run-" + uuid.uuid4().hex[:8]
        s = Settings(scenario=body.get("scenario", "genz-credit"), human_mode="api")
        gate = HumanGate("api", None, {"H2": {"choice": body["h2"], "id": body["h2"]}} if "h2" in body else {})
        o = Orchestrator(s, rid, body.get("request", "GenZ 특화 신용카드 만들어줘"), human=gate)
        gate.bus = o.run.bus
        RUNS[rid] = o

        def work():
            try:
                o.execute()
            except Exception as e:   # NeedsHuman 등: trace 에 run_end 가 이미 남는다
                o.run.bus.emit("run_end", None, f"중단: {type(e).__name__} {e}")
        threading.Thread(target=work, daemon=True).start()
        return {"run_id": rid}

    @app.get("/runs/{rid}/events")
    async def events(rid: str):
        o = RUNS.get(rid) or _404()
        q = o.run.bus.subscribe()
        past = list(o.run.bus.events)

        async def gen():
            for ev in past:
                yield o.run.bus.sse(ev)
            while True:
                try:
                    ev = await asyncio.get_event_loop().run_in_executor(None, lambda: q.get(timeout=1))
                except Exception:
                    continue
                yield o.run.bus.sse(ev)
                if ev["event"] == "run_end":
                    return
        return StreamingResponse(gen(), media_type="text/event-stream")

    @app.post("/runs/{rid}/human/{point}")
    def human(rid: str, point: str, body: dict | None = None):
        o = RUNS.get(rid) or _404()
        if point not in o.human.pending:
            raise HTTPException(409, f"{point} 는 대기 중이 아니다")
        o.human.resolve(point, body or None)
        return {"ok": True}

    @app.get("/runs/{rid}/result")
    def result(rid: str):
        o = RUNS.get(rid) or _404()
        p = f"{o.run.dir}/final/summary.json"
        if not os.path.exists(p):
            raise HTTPException(409, "아직 끝나지 않았다")
        return json.load(open(p, encoding="utf-8"))

    def _404():
        raise HTTPException(404, "run 없음")
    return app


def serve(host: str = "127.0.0.1", port: int = 8800):
    import uvicorn
    uvicorn.run(make_app(), host=host, port=port)
