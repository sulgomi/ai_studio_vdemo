"""저장된 실행 기록을 되돌려주는 provider. API 키 없이 오케스트레이터 전체를 시험한다(데모 모드).
scenarios/<이름>/<stage>/out.json 을 읽고, 재작업 전 시도는 out.attempt1.json 이 있으면 먼저 돌려준다."""
from __future__ import annotations

import json
import os

from .base import CallSpec, LLMResult


class PendingStage(Exception):
    """기록에 없는 단계. 입력을 내보내고 사람이(또는 하위 에이전트가) out.json 을 채운 뒤 다시 실행한다."""

    def __init__(self, stage: str, path: str, rotate: tuple | None = None):
        super().__init__(f"기록 없음: {stage} → {path}")
        self.stage, self.path, self.rotate = stage, path, rotate
        self.also: list = []


class ReplayProvider:
    def __init__(self, scenario_dir: str, pause: bool = False):
        self.dir = scenario_dir
        self.pause = pause
        self.seen: dict[str, int] = {}

    def _synth_labels(self, spec: CallSpec) -> LLMResult | None:
        """라벨링은 전체 라벨 맵(discovery/labels.all.json)에서 요청에 들어온 항목 id 만 잘라 돌려준다(청크 구성이 달라도 재생된다)."""
        path = os.path.join(self.dir, "discovery", "labels.all.json")
        if not (spec.stage.startswith("discovery/label.") and os.path.exists(path)):
            return None
        allmap = json.load(open(path, encoding="utf-8"))
        req = json.JSONDecoder().raw_decode(spec.user)[0]
        ids = [i["id"] for i in req["payload"]["items"]]
        res = {"labels": {i: allmap.get(i, {"needs": [], "tags": [], "domains": [], "relevance": "none"}) for i in ids}}
        env = {"status": "ok", "answer": "라벨링 기록", "result": res, "findings": [], "sources": [], "assumptions": [], "unresolved": [], "limits": [],
               "clarifications": [], "out_of_scope": {"detected": False, "suggested_agent": None}, "input_refs": []}
        return LLMResult(output=env, model="replay")

    def generate(self, spec: CallSpec) -> LLMResult:
        synth = self._synth_labels(spec)
        if synth:
            return synth
        stage = spec.stage.split("@")[0]      # 앙상블 변형 접미(@provider-model)는 같은 기록을 가리킨다
        n = self.seen[spec.stage] = self.seen.get(spec.stage, 0) + 1
        base = os.path.join(self.dir, stage)
        # n번째 호출 = out.attempt{n}.json (있으면), 마지막 시도는 out.json. 기록에 더 필요하면 멈춘다.
        attempts = 0
        while os.path.exists(os.path.join(base, f"out.attempt{attempts + 1}.json")):
            attempts += 1
        if n <= attempts:
            path = os.path.join(base, f"out.attempt{n}.json")
        elif n == attempts + 1:
            path = os.path.join(base, "out.json")
        else:      # 재작업이 더 필요한데 새 기록이 없다: 지금의 out.json 을 attempt{attempts+1} 로 돌리고 새 out.json 을 받는다
            if self.pause and os.path.exists(os.path.join(base, "out.json")):
                raise PendingStage(stage, os.path.join(base, "out.json"), rotate=(os.path.join(base, "out.json"), os.path.join(base, f"out.attempt{attempts + 1}.json")))
            if attempts == 0 and os.path.exists(os.path.join(base, "out.json")):
                path = os.path.join(base, "out.json")   # 1차 기록(시도 번호 없음): 되풀이 호출은 같은 기록을 쓴다
            else:
                raise FileNotFoundError(f"replay 재작업 기록 없음: {stage} (호출 {n}회째)")
        if not os.path.exists(path):
            if self.pause:
                raise PendingStage(stage, path)
            raise FileNotFoundError(f"replay 기록 없음: {path}")
        env = json.load(open(path, encoding="utf-8"))
        usage = env.get("usage") or {}
        return LLMResult(output=env, input_tokens=usage.get("input_tokens", 0), output_tokens=usage.get("output_tokens", 0),
                         tool_calls=0, model="replay")
