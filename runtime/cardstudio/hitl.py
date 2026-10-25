"""사람 확인 지점 H1~H5. 노드는 interrupt 앞에 LLM 호출·부작용을 두지 않는다(재개 시 처음부터 다시 실행되므로).
모드: auto(데모: 기본값 자동 승인, 기록은 남김) | cli(터미널 입력) | api(서버가 결정을 받을 때까지 대기)."""
from __future__ import annotations

import threading


class HumanGate:
    def __init__(self, mode: str = "auto", bus=None, overrides: dict | None = None):
        self.mode, self.bus = mode, bus
        self.overrides = overrides or {}          # {"H2": {"choice": 1}} 처럼 미리 정한 결정(재현·대안 분기용)
        self.pending: dict[str, dict] = {}
        self._events: dict[str, threading.Event] = {}

    def ask(self, point: str, prompt: str, options: list[dict], default: dict) -> dict:
        """options: [{id,label,...}]. 반환: 결정 dict(기본값 형식과 같음)."""
        self.bus.emit("human_wait", None, f"{point} {prompt}", point=point, options=options)
        if point in self.overrides:
            dec, how = self.overrides[point], "지정"
        elif self.mode == "auto":
            dec, how = default, "기본값 자동 승인"
        elif self.mode == "cli":
            for k, o in enumerate(options):
                print(f"  [{k}] {o.get('label', o.get('id'))}")
            raw = input(f"{point} {prompt} (엔터=기본값) > ").strip()
            dec, how = (options[int(raw)] if raw.isdigit() and int(raw) < len(options) else default), "사람 입력"
        else:   # api
            ev = self._events[point] = threading.Event()
            self.pending[point] = {"prompt": prompt, "options": options, "default": default, "decision": None}
            ev.wait()
            dec, how = self.pending.pop(point)["decision"] or default, "사람 결정(API)"
        self.bus.emit("human_decision", None, f"{point}: {how} → {dec.get('label', dec)}", point=point, decision=dec)
        return dec

    def resolve(self, point: str, decision: dict | None):
        """API 에서 호출: 대기 중인 지점에 결정을 넣고 풀어 준다."""
        self.pending[point]["decision"] = decision
        self._events[point].set()
