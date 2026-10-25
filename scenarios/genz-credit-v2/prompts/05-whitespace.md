당신은 카드 상품기획 에이전트 서비스의 '05-whitespace' 에이전트(whitespace) 역할을 실제로 한 번 수행한다(LLM 단계 실행). 한국어.

읽을 것(모두 /Users/sul/Workspace/ai-studio/final-mvp/ 아래):
1. agents/_common/common_rules.prompt.md (공통 규칙)
2. agents/05-whitespace/system_prompt.md (당신의 지시문. 규칙을 그대로 따른다), agents/05-whitespace/설계서.md, agents/05-whitespace/in.schema.json, agents/05-whitespace/out.schema.json
3. agents/_common/envelope.out.schema.json (출력 봉투)
4. 입력 봉투: scenarios/genz-credit-v2/05-whitespace/in.json  ← payload 에 이번 호출의 모든 근거가 들어 있다
5. 형식 참고용 이전 기록(내용은 베끼지 않는다): scenarios/genz-credit/05-whitespace/out.json

할 일: 입력 봉투를 보고 출력 봉투(JSON)를 scenarios/genz-credit-v2/05-whitespace/out.json 에 쓴다.
- 입력(payload)에 있는 자료만 근거로 쓴다. 웹 검색은 하지 않는다. 입력에 없는 수치·출처·사실을 만들지 않는다.
- 봉투: run_id/request_id/agent/contract_version 은 입력에서 복사, model 은 "claude-sonnet-5-5", status ok, answer 3문장 이내, result, findings/sources/assumptions/unresolved/limits/clarifications/out_of_scope/followups/input_refs 를 envelope.out.schema.json 에 맞춰 채운다(코드 전용 필드 usage, validation 은 쓰지 않는다). sources 는 payload 에 주어진 출처(docs 등)를 그대로 옮긴다.
- 쓰기 범위: 위 out.json 하나만 만들거나 고친다. 스크래치가 필요하면 /private/tmp/claude-501/-Users-sul-Workspace-ai-studio/9ea57029-1a10-4855-9ae6-5f37dd0e11d1/scratchpad/ 아래 '05whitespace_' 로 시작하는 이름만 쓴다. 다른 파일 수정 금지.

검증(반드시 실행해 통과시킬 것):
 cd /Users/sul/Workspace/ai-studio/final-mvp && PYTHONPATH=runtime /private/tmp/claude-501/-Users-sul-Workspace-ai-studio/9ea57029-1a10-4855-9ae6-5f37dd0e11d1/scratchpad/venv2/bin/python -W ignore -m cardstudio.validate_cli whitespace scenarios/genz-credit-v2/05-whitespace/in.json scenarios/genz-credit-v2/05-whitespace/out.json
 cd /Users/sul/Workspace/ai-studio/final-mvp/scenarios/genz-credit-v2 && /private/tmp/claude-501/-Users-sul-Workspace-ai-studio/9ea57029-1a10-4855-9ae6-5f37dd0e11d1/scratchpad/venv2/bin/python -W ignore harness.py validate 05-whitespace
둘 다 ok:true 가 될 때까지 out.json 을 고친다. 검증기가 불합리하게 막으면 코드를 고치지 말고 최종 보고에 어떤 규칙이 왜 막는지 적는다.
최종 보고: 'DONE 05-whitespace validate=ok|fail' 한 줄과 막힌 규칙이 있으면 짧게.