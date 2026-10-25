"""오케스트레이터가 코드로 하는 계산: 기회 점수, 컨셉 평가, 가상 고객 시뮬레이션, 에이전트별 검증기.
지금은 GenZ 시나리오 하네스(scenarios/genz-credit/harness.py)를 그대로 불러 쓰는 어댑터다.
TODO(이식): 하네스 함수를 이 패키지로 옮겨 시나리오 폴더 의존을 없앤다. 계산 규칙은 00 설계서 5절, 계수는 scenario.json sim_params."""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil


class LegacyHarness:
    def __init__(self, run_dir: str, scenario_dir: str):
        """run_dir 은 final-mvp/runs/<id>/ 여야 한다(하네스가 ROOT 를 두 단계 위로 잡는다)."""
        self.run_dir = run_dir
        os.makedirs(run_dir, exist_ok=True)
        shutil.copy(f"{scenario_dir}/scenario.json", f"{run_dir}/scenario.json")
        if os.path.exists(f"{scenario_dir}/competitor_db.json"):     # v2 하네스는 시나리오 폴더의 경쟁 카드 DB를 쓴다
            shutil.copy(f"{scenario_dir}/competitor_db.json", f"{run_dir}/competitor_db.json")
        path = f"{run_dir}/harness.py"
        src = open(f"{scenario_dir}/harness.py", encoding="utf-8").read()
        self.ns: dict = {"__file__": path, "__name__": "legacy_harness"}
        exec(compile(src, path, "exec"), self.ns)

    def _quiet(self, fn, *a):
        with contextlib.redirect_stdout(io.StringIO()):
            return fn(*a)

    def score_cells(self) -> list[dict]:
        return self._quiet(self.ns["score"])

    def ceiling_for_tags(self, seg_id: str, tags: list[str], domains: list[str] | None = None) -> float:
        """기회영역의 채택 천장: 지정한 혜택 방식 태그를 단 카드 격자 중 정적 손익 ≥ 3 을 지키는 최고 채택 의향.
        하네스 ceiling() 과 같은 격자인데, 니즈 대표 태그 대신 영역의 방식 태그를 쓴다."""
        ns, SC = self.ns, self.ns["SC"]
        seg = ns["SEG"][seg_id]
        order = sorted(seg["monthly_spend"], key=lambda c: -seg["monthly_spend"][c])
        order = [d for d in (domains or []) if d in order] + [c for c in order if c not in (domains or [])]   # 영역이 정해졌으면 그 영역에 혜택을 먼저 준다
        top_needs = [n for n in sorted(seg["need_weights"], key=lambda n: -seg["need_weights"][n]) if n != "invest"][:3]
        tg = list(tags)
        for n in top_needs:
            t = SC["need_tag_map"][n][0]
            if t not in tg:
                tg.append(t)
        best = 0.0
        for k in (2, 3):
            for r in (0.005, 0.01, 0.015, 0.02, 0.03):
                for cap in (0.5, 1.0, 1.5):
                    for fee in (0, 1, 2):
                        for mp in (20, 30):
                            card = {"rates": {c: r for c in order[:k]}, "capPerCat": cap, "fee": fee, "minPerf": mp, "cx": 0.3, "tags": tg}
                            if ns["static_profit"](card, seg_id) < 3:
                                continue
                            best = max(best, ns["simulate_card"](card, novelty=1.0, segs=[seg_id])["by_seg"][seg_id])
        return round(best, 3)

    def evaluate(self) -> dict:
        return self._quiet(self.ns["evaluate"])

    def simulate(self) -> dict:
        self._quiet(self.ns["simulate"])
        return json.load(open(f"{self.run_dir}/07-validation/twin.json", encoding="utf-8"))

    def code_checks(self, agent_dir: str, env_in: dict, env_out: dict):
        return self.ns["code_checks"](agent_dir, env_in, env_out)

    @property
    def scenario(self) -> dict:
        return self.ns["SC"]
