"""LLM 어댑터 경계. 모델 호출은 이 인터페이스 하나로만 나간다(provider 교체 = 클래스 교체)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol


class TransientLLMError(RuntimeError):
    """스로틀링·타임아웃 등 재시도 가능한 오류."""


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict
    run: Callable[[dict], dict]


@dataclass
class LLMResult:
    output: dict                      # submit_output 으로 받은 구조화 출력(봉투 out 의 LLM 담당 필드)
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    tool_calls: int = 0
    tool_urls: list = field(default_factory=list)   # 이번 호출의 도구 결과에 나온 URL(SRC-2 대조용)
    fetched: dict = field(default_factory=dict)     # web_fetch 로 받은 {url: 본문}(quote 대조용)
    model: str = ""


@dataclass
class CallSpec:
    agent: str
    model: str
    system: str
    user: str                         # 입력 봉투(JSON 문자열) + 재작업 지시
    output_schema: dict               # llm_output_schema(agent)
    tools: list = field(default_factory=list)
    max_tool_calls: int = 7
    max_tokens: int = 8000
    temperature: float = 0.2
    stage: str = ""                   # replay 가 기록을 찾는 키(실행 단계 이름)
    attempt: int = 1


class LLMProvider(Protocol):
    def generate(self, spec: CallSpec) -> LLMResult: ...
