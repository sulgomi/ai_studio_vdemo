# runtime: 설계서를 실제로 돌리는 코드

`agents/`의 설계서·지시문·스키마가 계약이고, 이 폴더는 그 계약을 **호출·검증·오케스트레이션**하는 Python 코드다.
LLM 호출 경계는 하나(`llm/`)라서 `replay`(저장된 기록), `anthropic`(Claude), `openai`(GPT)를 바꿔 끼운다. 로컬에서 직접 API를 부르는 구성이고 Bedrock은 쓰지 않는다(어댑터 파일은 AWS 이관 때 참고용으로만 남겼다). 웹 검색은 Tavily.

## 지금 상태

| 항목 | 상태 |
|---|---|
| 오케스트레이터 노드 순서, 게이트, 되돌림 상한, H1~H5, 기록 | 구현됨. `replay`로 GenZ 기본 실행(채택 0.383→0.412)과 H2 대안 분기(0.393→0.382)를 **저장된 기록과 같은 경로로 재현** |
| 10개 에이전트 입력 조립, 입력·출력 스키마 검증 | 구현됨. 매 호출 앞에서 입력 검증을 강제하고, LLM에게는 출력 스키마를 단일 도구(`submit_output`)로 강제 |
| LLM에게 줄 단일 스키마(외부 $ref 인라인) | 구현됨. 10개 에이전트의 기록된 출력이 모두 통과 |
| Anthropic / OpenAI provider | **초안(미검증)**. 도구 루프·재시도·URL 수집까지 짰고 가짜 클라이언트로 루프만 시험함. 키가 생기면 02 trend 한 건부터 확인. OpenAI 모델명은 `config.MODEL_IDS['openai']` 또는 환경변수로 계정의 실제 이름에 맞춘다(확인 필요) |
| 웹 검색 | **Tavily 연결 코드 있음**(`tools.TavilySearch`, 키 `TAVILY_API_KEY`). 실제 호출은 키가 생긴 뒤 확인. 발행일은 Tavily가 주는 경우에만 채우고 없으면 null |
| 시장기회 05 | **v2 엔진**(`opportunity.py`): 기회영역 = 세그먼트×니즈×공백 혜택 방식, 6축 점수, 가중치 흔들림 검사. 설계·프롬프트·스키마 갱신, LLM 단계는 GenZ로 한 번 실제 실행(`scenarios/genz-credit/05-whitespace-v2/`) |
| 계산 코드(기회 점수, 컨셉 평가, 시뮬레이션) | 시나리오 하네스를 어댑터로 호출. `code_steps.py`로 이식 필요 |
| 01 시장조사 총괄의 LLM 판단 | 고정 계획(trend∥competitor→consumer→종합). 01이 추가 호출을 정하는 부분은 2차 |
| 다음 셀로 이동, H4 재작업 요청, 기획서 보강 1라운드, 렌더러 | 2차(코드에 TODO와 중단 지점 표시) |
| 서버(SSE) | 코드 있음, fastapi 미설치 상태라 미실행 |

## 탐색 파이프라인 (에이전트 11~15)

근거 조사(scout) → 근거 색인 라벨링(labeler) → 공백 분석(gap_analyst, 각도별) → 반박 검증(critic, 렌즈별) → 아이디어 발산(ideator, 테마별) → 반박 검증 → 후보 확정(사람 확인 HD1). 흐름·집계·탈락은 코드(`discovery.py`, `tally.py`), 판단은 에이전트다.

```bash
python3 -m cardstudio discover --spec scenarios/genz-discovery/discovery.json --run-id disc-001          # replay(2026-10 GenZ 조사 기록 재생, 32회 호출)
python3 -m cardstudio discover --spec <spec> --provider anthropic --ensemble ideator=anthropic/opus,openai/opus --ensemble critic=openai/opus
```
- **다른 타깃으로 재현**: spec(`discovery.json`)의 target, 조사 주제(scouts), 각도(angles), 테마(themes), PM 방향만 바꾼다.
- **앙상블**: 에이전트를 서로 다른 계열 모델 여러 개로 돌려 합친다. 발산(scout/gap/ideator)은 합집합, 검증(critic)은 렌즈 안 중앙값(과반이 폐기해야 탈락), 라벨링은 과반. 검증은 발산과 다른 계열을 권장.
- 결과(`discovery_pack/`): `evidence_index.json`, `competitor_db.enriched.json`, `whitespace_candidates.json`, `ideas_ranked.json`, `new_tag_proposals.json`, `summary.json`. 메인 파이프라인은 `Settings.evidence_dir` 로 이 폴더를 읽는다.
- replay 기록(`scenarios/genz-discovery/discovery/`)은 `build_recordings.py` 가 `scenarios/genz-evidence/raw/`의 원본에서 만든다. 내용은 그대로이고 모양만 계약에 맞췄다(보정 1건은 스크립트 주석).

## 구조

```
cardstudio/
  config.py          모델 배정(에이전트→opus/sonnet/haiku→provider별 id), 상한(00 설계서 7절)
  contracts.py       스키마 로딩·검증, LLM용 단일 스키마 만들기
  llm/               base(CallSpec/LLMResult/ToolSpec) · replay · anthropic · openai (bedrock 은 미사용)
  tools.py           web_search(Tavily) / card_info_lookup / kb_search
  opportunity.py     05 기회영역 발굴·6축 점수·흔들림 검사(v2)
  discovery.py       탐색 파이프라인 오케스트레이터(11~15), tally.py 투표 집계, ensemble.py 앙상블 병합, evidence_build.py 근거 색인
  validators.py      출처 대조(SRC-1/2), 금칙어, 에이전트별 검증기 플러그인
  agent_runner.py    호출 하나 = 하네스 6단계(예산→입력검증→호출→출력검증→반려 시 1회 재요청→기록)
  payloads.py        단계별 입력 봉투 조립(앞 단계 결과에서 필드를 열거해 넣음)
  code_steps.py      기회 점수·컨셉 평가·시뮬레이션(지금은 하네스 어댑터)
  orchestrator.py    00 노드 순서·게이트·되돌림·H1~H5
  hitl.py            사람 확인 지점(auto / cli / api)
  events.py          trace 이벤트 + SSE 직렬화(UI trace.json 과 같은 모양)
  server.py          POST /runs, GET /runs/{id}/events(SSE), POST /runs/{id}/human/{H}
tests/test_runtime.py
```

## 실행

```bash
cd final-mvp
pip install -r runtime/requirements.txt          # 최소: jsonschema
export PYTHONPATH=runtime
cp runtime/.env.example runtime/.env             # TAVILY_API_KEY, ANTHROPIC_API_KEY 또는 OPENAI_API_KEY 입력
# 다른 프로젝트 .env 의 Tavily 키만 쓰려면(다른 키는 읽지 않음): export CARDSTUDIO_TAVILY_ENV=/경로/.env
python3 -m cardstudio.search_cli search "질의" --max 5      # 검색 CLI(에이전트가 Bash로 부름). 한도 초과 시 {"error":"HTTP 432"}

python3 -m cardstudio run --run-id demo-001                                   # GenZ 기본 실행(replay)
python3 -m cardstudio run --scenario genz-credit-alt --h2 1 --run-id demo-002 # H2에서 2순위 선택
python3 -m unittest discover -s runtime/tests -v

# 실제 호출(키 준비 후). 기회 탐색은 live 에서 자동으로 v2 엔진
python3 -m cardstudio run --provider anthropic --run-id live-001      # Claude
python3 -m cardstudio run --provider openai --run-id live-002         # GPT
```

결과는 `runs/<run-id>/`(Git 제외)에 단계 폴더(`06-concept/in.json·out.json·eval.json`…), `trace.json`, `final/기획서.md`, `final/summary.json`으로 남는다. 폴더 모양이 `scenarios/`와 같아서 기존 검증기·UI 빌더가 그대로 읽는다.

## 한 번의 에이전트 호출에서 일어나는 일

1. `payloads.Builder`가 앞 단계 결과에서 받을 필드만 골라 입력 봉투를 만든다.
2. `contracts`로 봉투와 payload를 검증한다. 틀리면 LLM을 부르지 않는다.
3. 시스템 프롬프트 = `_common/common_rules` + 에이전트 `system_prompt.md`(고정 순서라 캐시가 먹는다). 출력은 `submit_output` 도구 하나로 강제한다.
4. 코드가 `run_id`, `model`, `usage`, `validation` 등을 채운다. LLM이 같은 이름으로 쓴 값은 덮어쓴다.
5. 봉투·result 스키마 → 출처 대조(live에서는 이번 호출 도구 결과의 URL만 허용) → 에이전트별 검증기 순서로 검증한다.
6. 반려되면 `rework.prompt.md`로 반려 사유만 알려 1회 다시 요청한다. 두 번째 반려는 `NeedsHuman`으로 멈춘다.

## 실제 연결 전에 정할 것

1. 키 3개(Tavily, Anthropic 또는 OpenAI)를 `runtime/.env`에 넣는다.
2. OpenAI를 쓸 때 모델명 3개(opus/sonnet/haiku 자리)를 계정에서 쓰는 이름으로 정한다.
3. 경쟁사 DB와 KB의 실제 출처. 지금은 시장 카드 34종 JSON과 빈 KB다.
4. 01 시장조사 총괄을 LLM으로 둘지(설계서 방침) 고정 계획으로 시작할지.
5. 실행 상태 저장소: 지금은 파일 체크포인트. AWS에서는 Step Functions + DynamoDB/S3로 바꾼다(노드가 멱등이라 옮기기 쉽다).

## 처음 실제로 돌릴 때의 순서 제안

1. `provider=anthropic`(또는 openai)으로 **02 trend 한 건**만(Tavily 연결 포함) → 검증 통과율, 토큰, 소요 시간 확인.
2. 04 consumer, 03 competitor 순으로 늘린다. 03은 DB 도구만 써서 비용이 작다.
3. 06 concept 이후는 입력이 앞 단계 기록이라, 앞 단계는 replay로 두고 **뒷단만 실제로** 바꿔 돌릴 수 있다(`--provider anthropic --live-stages 06,07,08`: 지정한 단계만 실제 호출하고 나머지는 replay).
4. 전체를 실제로 한 번 돌려 replay 기록과 승자·채택 의향이 얼마나 달라지는지 본다(실행마다 컨셉이 바뀌는 것은 알려진 한계다).

## GenZ v2 시나리오 재생과 기록

```
PYTHONPATH=runtime python3 -m cardstudio run --scenario genz-credit-v2-alt --h2 0   # 구독노트(1순위)
PYTHONPATH=runtime python3 -m cardstudio run --scenario genz-credit-v2 --h2 2       # 꾸준(3순위)
```

새 기록은 `scenarios/genz-credit-v2/record.py`(환경변수 `RECORD_SCENARIO`)가 다음에 필요한 단계를 알려 주고, 각 단계의 `prompts/*.md`를 에이전트에 줘서 채운다. 설명은 `scenarios/genz-credit-v2/README.md`.
