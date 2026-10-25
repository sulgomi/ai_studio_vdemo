"""실행 기록(trace) 이벤트. UI의 trace.json 과 같은 모양이라 화면이 그대로 읽는다.
event: run_start|route|human_wait|human_decision|call|result|validate|reject|rework|code|gate|code_fix|run_end"""
from __future__ import annotations

import json
import os
import queue
import threading
from datetime import datetime, timezone


class EventBus:
    def __init__(self, path: str | None = None):
        self.path, self.events, self.subs = path, [], []
        self._lock = threading.Lock()

    def emit(self, event: str, agent: str | None, detail: str, **extra) -> dict:
        with self._lock:
            ev = {"seq": len(self.events) + 1, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "event": event, "agent": agent, "detail": detail, **extra}
            self.events.append(ev)
            if self.path:
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                json.dump(self.events, open(self.path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            for q in self.subs:
                q.put(ev)
        return ev

    def subscribe(self) -> "queue.Queue":
        q: queue.Queue = queue.Queue()
        self.subs.append(q)
        return q

    @staticmethod
    def sse(ev: dict) -> str:
        return f"event: {ev['event']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
