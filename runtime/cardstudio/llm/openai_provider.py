"""OpenAI(GPT) provider. Anthropic 과 같은 구조: 출력은 submit_output 함수 하나로 강제하고, 다른 도구는 auto.
스키마 엄격 모드(strict)는 쓰지 않는다. 대신 우리 검증기(contracts)가 받아서 걸러 내고 반려한다.
미검증 초안: OPENAI_API_KEY 가 생기면 02 trend 한 건부터 확인. 모델명은 config.MODEL_IDS['openai'] 에서 확인 필요."""
from __future__ import annotations

import json
import time

from .base import CallSpec, LLMResult, TransientLLMError

SUBMIT = "submit_output"


class OpenAIProvider:
    def __init__(self, client=None, api_key: str | None = None):
        if client is None:
            import openai  # 지연 import
            client = openai.OpenAI(api_key=api_key)
        self.client = client

    def generate(self, spec: CallSpec) -> LLMResult:
        fn = lambda name, desc, schema: {"type": "function", "function": {"name": name, "description": desc, "parameters": schema}}
        tools = [fn(t.name, t.description, t.input_schema) for t in spec.tools]
        tools.append(fn(SUBMIT, "최종 출력을 제출한다. 스키마에 맞는 JSON만 넣는다.", spec.output_schema))
        by_name = {t.name: t for t in spec.tools}
        msgs = [{"role": "system", "content": spec.system}, {"role": "user", "content": spec.user}]
        res = LLMResult(output={}, model=spec.model)
        used = 0
        while True:
            force = used >= spec.max_tool_calls or not spec.tools
            choice = {"type": "function", "function": {"name": SUBMIT}} if force else "auto"
            # temperature 는 보내지 않는다(추론형 모델은 기본값만 허용하는 경우가 있다)
            resp = self._call(dict(model=spec.model, messages=msgs, tools=tools, tool_choice=choice, max_completion_tokens=spec.max_tokens))
            u = resp.usage
            res.input_tokens += getattr(u, "prompt_tokens", 0) or 0
            res.output_tokens += getattr(u, "completion_tokens", 0) or 0
            det = getattr(u, "prompt_tokens_details", None)
            res.cached_tokens += (getattr(det, "cached_tokens", 0) or 0) if det else 0
            msg = resp.choices[0].message
            calls = list(msg.tool_calls or [])
            final = next((c for c in calls if c.function.name == SUBMIT), None)
            if final:
                res.output, res.tool_calls = json.loads(final.function.arguments), used
                return res
            msgs.append(msg.model_dump(exclude_none=True) if hasattr(msg, "model_dump") else msg)
            if not calls:
                msgs.append({"role": "user", "content": "submit_output 함수로 최종 출력을 제출해."})
                used = spec.max_tool_calls
                continue
            for c in calls:
                used += 1
                try:
                    out = by_name[c.function.name].run(json.loads(c.function.arguments or "{}"))
                    res.tool_urls += [r["url"] for r in out.get("results", []) if isinstance(r, dict) and r.get("url")]
                    if isinstance(out, dict) and out.get("url") and not out.get("error"):   # web_fetch
                        res.tool_urls.append(out["url"])
                        res.fetched[out["url"]] = out.get("text", "")
                    content = json.dumps(out, ensure_ascii=False)
                except Exception as e:
                    content = json.dumps({"error": str(e)[:300]}, ensure_ascii=False)
                msgs.append({"role": "tool", "tool_call_id": c.id, "content": content})

    def _call(self, kwargs, retries: int = 3):
        for k in range(retries):
            try:
                return self.client.chat.completions.create(**kwargs)
            except Exception as e:
                name = type(e).__name__
                if name in ("RateLimitError", "APIConnectionError", "APITimeoutError", "InternalServerError") and k < retries - 1:
                    time.sleep(2 ** k * 2)
                    continue
                raise TransientLLMError(name) if name in ("RateLimitError", "APIConnectionError", "APITimeoutError") else e
