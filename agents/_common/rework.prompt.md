[재작업 지시 템플릿: 오케스트레이터가 검증 반려 후 같은 에이전트를 다시 부를 때 user 메시지로 넣는다]

이전 출력이 검증을 통과하지 못했다. 아래 반려 사유만 고쳐서 같은 스키마로 다시 출력한다.

- 재작업 회차: {{attempt}} / 최대 {{max_attempts}}
- 이전 출력: {{previous_output_ref}} (아래 JSON)
- 반려 사유:
{{#reasons}}
  - [{{code}}] {{path}}: {{message}}
{{/reasons}}

규칙
1. 사유에 적힌 경로의 값만 고친다. 다른 필드는 이전 출력과 같게 둔다.
2. 사유가 NUMBER_NOT_IN_INPUT이면 그 수치를 지우거나 입력에 있는 값으로 바꾼다. 새 수치를 만들지 않는다.
3. 사유가 SOURCE_URL_UNKNOWN이면 그 출처를 지우고, 받친 주장은 estimate로 바꾸거나 지운다.
4. 사유가 GATE_FAILED이면 message에 적힌 지표가 왜 미달인지 먼저 assumptions에 한 줄로 쓰고, 그 지표를 움직이는 설계 요소(혜택률, 한도, 조건, 대상)를 바꾼다.
5. 같은 실수를 반복하지 않는다. 고친 내용을 assumptions 끝에 "재작업 {{attempt}}: 무엇을 바꿨는지" 한 줄로 남긴다.

[이전 출력]
{{previous_output_json}}
