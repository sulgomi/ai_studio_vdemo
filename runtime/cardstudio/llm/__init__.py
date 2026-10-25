from __future__ import annotations

from .base import CallSpec, LLMProvider, LLMResult, ToolSpec, TransientLLMError  # noqa: F401


def make_provider(name: str, scenario_dir: str | None = None, region: str = "ap-northeast-2", pause: bool = False):
    if name == "replay":
        from .replay_provider import ReplayProvider
        return ReplayProvider(scenario_dir, pause=pause)
    if name == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    if name == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider()
    if name == "bedrock":
        from .bedrock_provider import BedrockProvider
        return BedrockProvider(region=region)
    raise ValueError(f"unknown provider {name}")


class MixedProvider:
    """단계별로 provider 를 섞는다. 예: 02~05 는 replay(기록), 06 이후만 실제 호출.
    live_stages 에 든 단계 폴더 이름(접두 일치)만 live 로 보낸다."""

    def __init__(self, live, replay, live_stages):
        self.live, self.replay, self.live_stages = live, replay, tuple(live_stages)

    def generate(self, spec):
        use_live = any(spec.stage.startswith(p) for p in self.live_stages)
        return (self.live if use_live else self.replay).generate(spec)
