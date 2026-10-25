"""에이전트 한 번 호출 = 00 설계서 6절 하네스.
1 예산 확인 → 2 입력 검증 → 3 LLM 호출(구조화 출력) → 4 출력 검증 → 5 반려 시 1회 재요청, 두 번째 반려는 사람 확인 큐 → 6 기록."""
from __future__ import annotations

import copy
import json
import os
import threading
import time

from . import contracts, validators
from .config import AGENT_DIR, AGENT_MODEL, AGENT_TOOLS, AGENTS_DIR, CRITIC_LENS_MODEL, CRITIC_TOOL_LENSES, Settings
from .events import EventBus
from .llm.base import CallSpec
from .tools import build_tools


class NeedsHuman(Exception):
    """재시도 상한을 넘겨 사람 확인 큐로 보낸다."""

    def __init__(self, stage, rejects):
        super().__init__(f"{stage}: 반려 {len(rejects)}건")
        self.stage, self.rejects = stage, rejects


def system_prompt(agent: str) -> str:
    """공통 규칙 + 에이전트 지시문. 항상 같은 순서·같은 내용이라 prompt caching 이 먹는다."""
    common = open(f"{AGENTS_DIR}/_common/common_rules.prompt.md", encoding="utf-8").read()
    own = open(f"{AGENTS_DIR}/{AGENT_DIR[agent]}/system_prompt.md", encoding="utf-8").read()
    return common.strip() + "\n\n---\n\n" + own.strip()


def rework_text(attempt: int, max_attempts: int, prev: dict, reasons: list[dict]) -> str:
    t = open(f"{AGENTS_DIR}/_common/rework.prompt.md", encoding="utf-8").read()
    lines = "\n".join(f"  - [{r['code']}] {r['path']}: {r['message']}" for r in reasons)
    t = t.replace("{{attempt}}", str(attempt)).replace("{{max_attempts}}", str(max_attempts))
    t = t.replace("{{previous_output_ref}}", "직전 출력").replace("{{previous_output_json}}", json.dumps(prev, ensure_ascii=False))
    start, end = t.index("{{#reasons}}"), t.index("{{/reasons}}") + len("{{/reasons}}")
    return t[:start] + lines + t[end:]


class AgentRunner:
    def __init__(self, settings: Settings, provider, bus: EventBus, run_dir: str, legacy=None, search=None, db=None, kb=None):
        self.s, self.provider, self.bus, self.run_dir, self.legacy = settings, provider, bus, run_dir, legacy
        self.search, self.db, self.kb = search, db, kb
        self._lock = threading.Lock()
        self.usage_total = {"input_tokens": 0, "output_tokens": 0, "calls": 0, "tool_calls": 0, "seconds": 0.0}

    def call(self, stage: str, agent: str, env_in: dict, *, label: str = "", provider=None, model: str | None = None) -> dict:
        """stage: 결과를 저장할 폴더 이름(예: 06-concept). 반환: 검증을 통과한 출력 봉투."""
        lim = self.s.limits
        errs = contracts.validate_envelope_in(agent, env_in)
        if errs:   # 입력이 틀리면 LLM 을 부르지 않는다(비용 방지)
            raise ValueError(f"입력 검증 실패 {stage}: {errs[:3]}")
        self._save(stage, "in.json", env_in)
        self.bus.emit("call", agent, label or f"{stage} 호출 ({model or self.model_for(agent, env_in)})")
        prev, reasons = None, None
        for attempt in range(1, lim.agent_retry + 2):
            user_env = copy.deepcopy(env_in)
            body = json.dumps(user_env, ensure_ascii=False)
            if reasons:
                user_env["rework"] = {"attempt": attempt - 1, "reasons": reasons, "previous_output_ref": f"{stage}/out.attempt{attempt - 1}.json"}
                body = json.dumps(user_env, ensure_ascii=False) + "\n\n" + rework_text(attempt - 1, lim.agent_retry, prev, reasons)
            spec = CallSpec(agent=agent, model=model or self.model_for(agent, env_in), system=system_prompt(agent), user=body,
                            output_schema=contracts.llm_output_schema(agent),
                            tools=build_tools(agent, search=self.search, db=self.db, kb=self.kb, names=self.tool_names(agent, env_in)),
                            max_tool_calls=env_in.get("budget", {}).get("max_tool_calls", lim.tool_calls_per_call),
                            max_tokens=env_in.get("budget", {}).get("max_output_tokens", lim.max_output_tokens),
                            stage=stage, attempt=attempt)
            t0 = time.time()
            res = (provider or self.provider).generate(spec)
            sec = round(time.time() - t0, 2)
            out = self._finalize(res.output, env_in, res, sec)
            live = res.model != "replay"   # 기록 재생 결과에는 이번 호출의 도구 URL이 없으므로 SRC-2 대조를 건너뛴다
            problems = contracts.validate_envelope_out(agent, out)
            if not problems:
                v = validators.run_all(AGENT_DIR[agent], env_in, out, tool_urls=set(res.tool_urls) if live else None, legacy=self.legacy,
                                       fetched=res.fetched if live else None)
                problems = v["rejects"]
                out["validation"] = {"passed": not problems, "warnings": v["warnings"], "rejects": problems}
            self._usage(res, sec)
            if not problems:
                self._save(stage, "out.json", out)
                self.bus.emit("validate", agent, "검증 통과" + (f" (경고 {len(out['validation']['warnings'])})" if out["validation"]["warnings"] else ""))
                return out
            self.bus.emit("reject", agent, f"검증 반려 {len(problems)}건 (시도 {attempt}): " + "; ".join(f"[{p['code']}] {p['path']}" for p in problems[:3]))
            self._save(stage, f"out.attempt{attempt}.json", out)
            prev, reasons = out, problems
        raise NeedsHuman(stage, reasons)

    def model_for(self, agent: str, env_in: dict) -> str:
        if agent == "critic":   # 렌즈마다 모델이 다르다
            return self.s.model_id(agent, CRITIC_LENS_MODEL.get(env_in["payload"]["lens"]["id"]))
        return self.s.model_id(agent)

    def tool_names(self, agent: str, env_in: dict) -> list:
        if agent == "critic":
            return ["web_search", "web_fetch"] if env_in["payload"]["lens"]["id"] in CRITIC_TOOL_LENSES and env_in["payload"].get("search_available", True) else []
        return AGENT_TOOLS.get(agent, [])

    # ---- 내부 -----------------------------------------------------------------------
    def _finalize(self, raw: dict, env_in: dict, res, sec: float) -> dict:
        """코드가 쓰는 필드를 채운다. LLM 이 쓴 같은 이름 필드는 덮어쓴다."""
        out = copy.deepcopy(raw)
        out.update(run_id=env_in["run_id"], request_id=env_in["request_id"], agent=env_in["agent"],
                   contract_version=env_in["contract_version"], model=res.model or out.get("model", ""))
        out.setdefault("input_refs", [])
        out["usage"] = {"input_tokens": res.input_tokens, "output_tokens": res.output_tokens, "seconds": sec,
                        "tool_calls": res.tool_calls, "cached": bool(res.cached_tokens)}
        return out

    def _usage(self, res, sec):
        with self._lock:
            self._usage_locked(res, sec)

    def _usage_locked(self, res, sec):
        u = self.usage_total
        u["input_tokens"] += res.input_tokens
        u["output_tokens"] += res.output_tokens
        u["calls"] += 1
        u["tool_calls"] += res.tool_calls
        u["seconds"] = round(u["seconds"] + sec, 2)

    def _save(self, stage, name, data):
        d = os.path.join(self.run_dir, stage)
        os.makedirs(d, exist_ok=True)
        json.dump(data, open(os.path.join(d, name), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    def archive(self, stage: str, files=("in.json", "out.json", "eval.json", "twin.json")):
        """재작업 직전, 이전 결과를 *.attemptN.json 으로 보관(기획서의 결정 이력과 비교에 쓴다)."""
        d = os.path.join(self.run_dir, stage)
        for f in files:
            p = os.path.join(d, f)
            if os.path.exists(p):
                stem, ext = os.path.splitext(f)
                n = 1
                while os.path.exists(os.path.join(d, f"{stem}.attempt{n}{ext}")):
                    n += 1
                os.replace(p, os.path.join(d, f"{stem}.attempt{n}{ext}"))
