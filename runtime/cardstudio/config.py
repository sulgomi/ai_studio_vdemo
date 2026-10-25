"""설정 한 곳. 모델 배정은 03_모델_추천.md, 상한은 agents/00-orchestrator/설계서.md 7절."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))
MVP = os.path.dirname(os.path.dirname(HERE))            # final-mvp/


def load_env():
    """runtime/.env 또는 final-mvp/.env 의 KEY=VALUE 를 환경변수로(이미 있는 값은 덮어쓰지 않음). 라이브러리 없이."""
    for p in (os.path.join(MVP, "runtime", ".env"), os.path.join(MVP, ".env")):
        if not os.path.exists(p):
            continue
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


load_env()
AGENTS_DIR = os.path.join(MVP, "agents")
RUNS_DIR = os.path.join(MVP, "runs")                    # 실행 결과 저장 위치(Git 제외 권장)

# 에이전트 id(봉투의 agent) → agents/ 폴더
AGENT_DIR = {
    "research_lead": "01-research-lead", "trend": "02-trend", "competitor": "03-competitor",
    "consumer": "04-consumer", "whitespace": "05-whitespace", "concept": "06-concept",
    "validation": "07-validation", "guardrail": "08-guardrail",
    "design_marketing": "09-design-marketing", "plan_doc": "10-plan-doc",
    # 탐색 파이프라인(근거 조사 → 공백 분석 → 아이디어 → 반박 검증)
    "scout": "11-scout", "gap_analyst": "12-gap-analyst", "ideator": "13-ideator", "critic": "14-critic", "labeler": "15-labeler",
}

# 논리 모델 이름 → provider별 실제 모델 id. 새 모델이 나오면 여기만 고친다.
MODEL_IDS = {
    "anthropic": {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5"},
    # OpenAI 모델명은 계정에서 쓸 수 있는 이름으로 바꿔야 한다(확인 필요). 환경변수로도 덮어쓴다:
    # OPENAI_MODEL_OPUS / OPENAI_MODEL_SONNET / OPENAI_MODEL_HAIKU
    "openai": {"opus": os.environ.get("OPENAI_MODEL_OPUS", "gpt-5"), "sonnet": os.environ.get("OPENAI_MODEL_SONNET", "gpt-5-mini"),
               "haiku": os.environ.get("OPENAI_MODEL_HAIKU", "gpt-5-nano")},
    # 로컬 개발에서는 쓰지 않는다(AWS 이관 시 참고용으로만 남김).
    "bedrock": {"opus": "TODO-bedrock-opus-profile", "sonnet": "TODO-bedrock-sonnet-profile", "haiku": "TODO-bedrock-haiku-profile"},
    "replay": {"opus": "replay", "sonnet": "replay", "haiku": "replay"},
}

# 에이전트별 논리 모델(03_모델_추천.md)
AGENT_MODEL = {
    "research_lead": "sonnet", "trend": "sonnet", "competitor": "haiku", "consumer": "haiku",
    "whitespace": "sonnet", "concept": "sonnet", "validation": "sonnet", "guardrail": "sonnet",
    "design_marketing": "opus", "plan_doc": "sonnet",
    "scout": "sonnet", "gap_analyst": "sonnet", "ideator": "opus", "critic": "opus", "labeler": "haiku",
}
# 렌즈마다 모델을 달리하는 critic (14 설계서 10절)
CRITIC_LENS_MODEL = {"existing": "opus", "risk": "opus", "novelty": "opus", "evidence": "sonnet"}
# 도구를 쓰는 에이전트(agents/_common/tools.schema.json)
AGENT_TOOLS = {
    "trend": ["web_search", "kb_search"], "competitor": ["card_info_lookup", "web_search"],
    "consumer": ["web_search", "kb_search"], "research_lead": [],
    "scout": ["web_search", "web_fetch"], "gap_analyst": ["web_search", "web_fetch"], "ideator": [], "labeler": [],
    "critic": [],   # 렌즈가 existing/novelty 일 때만 agent_runner 가 web_search, web_fetch 를 붙인다
}
CRITIC_TOOL_LENSES = {"existing", "novelty"}


@dataclass
class Limits:
    """00 설계서 7절 상한. 하나라도 빠지면 비용이 폭주한다."""
    max_regressions: int = 8            # 실행 전체 회귀(되돌림) 수
    agent_retry: int = 1                # 검증 반려 재시도(에이전트별)
    concept_rework: int = 3             # 컨셉 재작업 합계(채택 미달 2 + 가드레일 fix 1)
    guardrail_rework: int = 1
    adopt_rework: int = 2
    tool_calls_per_call: int = 7        # 에이전트 한 번 호출 안 도구 호출 수
    seconds_per_call: int = 240
    max_output_tokens: int = 8000
    run_seconds_warn: int = 900


@dataclass
class Settings:
    provider: str = os.environ.get("CARDSTUDIO_PROVIDER", "replay")   # replay | anthropic | openai
    region: str = os.environ.get("AWS_REGION", "ap-northeast-2")
    runs_dir: str = RUNS_DIR
    limits: Limits = field(default_factory=Limits)
    # 사람 확인 지점 처리: auto(데모, 기본값 자동 승인) | cli(터미널 입력) | api(서버가 대기)
    human_mode: str = os.environ.get("CARDSTUDIO_HUMAN", "auto")
    scenario: str = "genz-credit"
    discovery_scenario: str = "genz-discovery"   # 탐색 파이프라인 replay 기록 폴더(scenarios/ 아래)
    # 기회 탐색 엔진: v2(기회영역=세그먼트×니즈×공백 방식) | legacy(세그먼트×니즈). replay 기록은 legacy 로 만들어져 기본 legacy
    opportunity_engine: str = ""
    # 근거 팩 폴더(evidence_index.json, competitor_db.enriched.json). 비우면 근거 연결 없이 기존 방식
    evidence_dir: str = ""
    template_scenario: str = "genz-credit"   # 입력 틀(in.json)의 고정 부분을 가져올 시나리오. 현재 시나리오에 없으면 여기서
    pause_on_missing: bool = False           # replay 기록에 없는 단계에서 멈추고 입력을 내보낸다(기록 만들기용)
    # 앙상블: 에이전트 → ["provider/logical_model", ...]. 비우면 단일 호출. 예: {"ideator": ["anthropic/opus", "openai/opus"]}
    ensembles: dict = field(default_factory=dict)
    # 시나리오 폴더 안 scenario.json 이 기준일·세그먼트·가정치를 가진다.
    scenarios_dir: str = os.path.join(MVP, "scenarios")

    def engine(self) -> str:
        if self.opportunity_engine:
            return self.opportunity_engine
        if self.scenario not in ("genz-credit", "genz-credit-alt"):      # v1 기록 시나리오만 legacy(기록과 같은 경로 재현)
            return "v2"
        return "legacy" if self.provider == "replay" else "v2"

    def model_id(self, agent: str, logical: str | None = None, provider: str | None = None) -> str:
        return MODEL_IDS[provider or self.provider][logical or AGENT_MODEL[agent]]
