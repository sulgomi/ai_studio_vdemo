"""Bedrock Converse API provider(AWS 이관용). anthropic_provider 와 같은 루프, 호출 형식만 다르다.
구조화 출력: toolConfig 의 submit_output 도구 + toolChoice. 미검증 초안: 모델 id·리전·권한은 SA가 확정.
Bedrock 쪽 skills/서브에이전트 기능에 의존하지 않고 프롬프트+스키마+toolConfig 만 쓴다."""
from __future__ import annotations

import json
import time

from .base import CallSpec, LLMResult, TransientLLMError

SUBMIT = "submit_output"


class BedrockProvider:
    def __init__(self, region: str = "ap-northeast-2", client=None):
        if client is None:
            import boto3  # 지연 import
            client = boto3.client("bedrock-runtime", region_name=region)
        self.client = client

    def generate(self, spec: CallSpec) -> LLMResult:
        specs = [{"toolSpec": {"name": t.name, "description": t.description, "inputSchema": {"json": t.input_schema}}} for t in spec.tools]
        specs.append({"toolSpec": {"name": SUBMIT, "description": "최종 출력을 제출한다.", "inputSchema": {"json": spec.output_schema}}})
        by_name = {t.name: t for t in spec.tools}
        msgs = [{"role": "user", "content": [{"text": spec.user}]}]
        res = LLMResult(output={}, model=spec.model)
        used = 0
        while True:
            force = used >= spec.max_tool_calls or not spec.tools
            choice = {"tool": {"name": SUBMIT}} if force else {"auto": {}}
            resp = self._call(dict(modelId=spec.model, system=[{"text": spec.system}], messages=msgs,
                                   toolConfig={"tools": specs, "toolChoice": choice},
                                   inferenceConfig={"maxTokens": spec.max_tokens, "temperature": spec.temperature}))
            u = resp.get("usage", {})
            res.input_tokens += u.get("inputTokens", 0)
            res.output_tokens += u.get("outputTokens", 0)
            content = resp["output"]["message"]["content"]
            uses = [c["toolUse"] for c in content if "toolUse" in c]
            final = next((t for t in uses if t["name"] == SUBMIT), None)
            if final:
                res.output, res.tool_calls = final["input"], used
                return res
            msgs.append({"role": "assistant", "content": content})
            if not uses:
                msgs.append({"role": "user", "content": [{"text": "submit_output 도구로 최종 출력을 제출해."}]})
                used = spec.max_tool_calls
                continue
            blocks = []
            for t in uses:
                used += 1
                try:
                    out = by_name[t["name"]].run(t["input"])
                    res.tool_urls += [r["url"] for r in out.get("results", []) if isinstance(r, dict) and r.get("url")]
                    if isinstance(out, dict) and out.get("url") and not out.get("error"):   # web_fetch
                        res.tool_urls.append(out["url"])
                        res.fetched[out["url"]] = out.get("text", "")
                    blocks.append({"toolResult": {"toolUseId": t["toolUseId"], "content": [{"json": out}]}})
                except Exception as e:
                    blocks.append({"toolResult": {"toolUseId": t["toolUseId"], "content": [{"text": str(e)[:300]}], "status": "error"}})
            msgs.append({"role": "user", "content": blocks})

    def _call(self, kwargs, retries: int = 3):
        for k in range(retries):
            try:
                return self.client.converse(**kwargs)
            except Exception as e:
                if type(e).__name__ in ("ThrottlingException", "ModelTimeoutException", "ServiceUnavailableException") and k < retries - 1:
                    time.sleep(2 ** k * 2)
                    continue
                raise TransientLLMError(type(e).__name__) if "Throttl" in type(e).__name__ else e
