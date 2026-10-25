"""Anthropic Messages API provider. 구조화 출력은 '단일 도구 강제' 방식: submit_output 도구의 input_schema 를
출력 스키마로 두고, 다른 도구(web_search 등)를 쓰는 동안은 auto, 상한에 닿으면 submit_output 을 강제한다.
미검증 초안: 키가 생기면 tests/live_smoke.py 로 02 trend 한 건부터 확인한다."""
from __future__ import annotations

import json
import time

from .base import CallSpec, LLMResult, TransientLLMError

SUBMIT = "submit_output"


class AnthropicProvider:
    def __init__(self, client=None, api_key: str | None = None):
        if client is None:
            import anthropic  # 지연 import
            client = anthropic.Anthropic(api_key=api_key)
        self.client = client

    def generate(self, spec: CallSpec) -> LLMResult:
        tools = [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in spec.tools]
        tools.append({"name": SUBMIT, "description": "최종 출력을 제출한다. 스키마에 맞는 JSON만 넣는다.", "input_schema": spec.output_schema})
        by_name = {t.name: t for t in spec.tools}
        msgs = [{"role": "user", "content": spec.user}]
        usage = LLMResult(output={}, model=spec.model)
        used = 0
        while True:
            force = used >= spec.max_tool_calls or not spec.tools
            kwargs = dict(model=spec.model, max_tokens=spec.max_tokens, temperature=spec.temperature,
                          system=[{"type": "text", "text": spec.system, "cache_control": {"type": "ephemeral"}}],
                          messages=msgs, tools=tools,
                          tool_choice={"type": "tool", "name": SUBMIT} if force else {"type": "auto"})
            resp = self._call(kwargs)
            usage.input_tokens += resp.usage.input_tokens
            usage.output_tokens += resp.usage.output_tokens
            usage.cached_tokens += getattr(resp.usage, "cache_read_input_tokens", 0) or 0
            uses = [b for b in resp.content if b.type == "tool_use"]
            final = next((b for b in uses if b.name == SUBMIT), None)
            if final:
                usage.output, usage.tool_calls = final.input, used
                return usage
            if not uses:   # 도구 없이 말만 한 경우: 제출을 강제하고 한 번 더
                msgs.append({"role": "assistant", "content": resp.content})
                msgs.append({"role": "user", "content": "submit_output 도구로 최종 출력을 제출해."})
                used = spec.max_tool_calls
                continue
            msgs.append({"role": "assistant", "content": resp.content})
            results = []
            for b in uses:
                used += 1
                try:
                    out = by_name[b.name].run(b.input)
                    usage.tool_urls += [r["url"] for r in out.get("results", []) if isinstance(r, dict) and r.get("url")]
                    if isinstance(out, dict) and out.get("url") and not out.get("error"):   # web_fetch
                        usage.tool_urls.append(out["url"])
                        usage.fetched[out["url"]] = out.get("text", "")
                    results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out, ensure_ascii=False)})
                except Exception as e:   # 도구 실패는 모델에게 알려 다른 길을 찾게 한다
                    results.append({"type": "tool_result", "tool_use_id": b.id, "is_error": True, "content": str(e)[:300]})
            msgs.append({"role": "user", "content": results})

    def _call(self, kwargs, retries: int = 3):
        for k in range(retries):
            try:
                return self.client.messages.create(**kwargs)
            except Exception as e:   # anthropic.RateLimitError / APIConnectionError 등
                name = type(e).__name__
                if name in ("RateLimitError", "APIConnectionError", "APITimeoutError", "InternalServerError") and k < retries - 1:
                    time.sleep(2 ** k * 2)
                    continue
                raise TransientLLMError(name) if name in ("RateLimitError", "APIConnectionError", "APITimeoutError") else e
