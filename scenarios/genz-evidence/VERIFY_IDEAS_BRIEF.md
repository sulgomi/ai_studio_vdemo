# 컨셉 아이디어 적대적 검증 공통 과제

`raw/idea_growth.json`(GRI1~8), `idea_performance.json`(PRI1~8), `idea_trend.json`(TDI1~7), `idea_fresh.json`(FRI1~9) — 총 32개 `ideas[]`는 GenZ 신용카드 데모의 컨셉 후보다. 아이디어는 가설이고, 작성자는 자기 아이디어를 좋게 쓰기 쉽다. 당신은 **반박하는 검증자**다. 살리려 하지 말고 무너뜨릴 수 있는지 먼저 시도한다. 근거 없이 지지하지도, 근거 없이 반박하지도 않는다.

읽을 것(`scenarios/genz-evidence/` 기준, 읽기 전용): `IDEATION_BRIEF.md`(아이디어 모양과 규칙), 위 idea 파일 4개, 근거 raw 전체(`stats`, `trends`, `consumer`, `wide`, `suneung`, `gatherings`, `viral`, `money`, `invest`, `learning`, `performance`, `foresight`), `competitor_db.enriched.json`(경쟁 카드 50종), `whitespace_candidates.json`(앞선 공백 검증 결과).

## 출력 (`raw/verify_ideas_<렌즈>.json`, UTF-8, 한국어)
```json
{
  "lens": "렌즈", "search_available": true,
  "checks": [
    {"idea_id": "GRI1", "vote": "confirm | weaken | refute",
     "findings": ["시도한 반박과 결과. 근거 id나 읽은 URL"],
     "corrections": ["아이디어 서술에서 고칠 점(과장, 잘못 읽은 근거, 놓친 기존 카드/규정 등)"],
     "rating": "A 유망 | B 보완 필요 | C 약함 | X 폐기",
     "confidence_in_vote": "high | medium | low",
     "lens_fields": {}}
  ],
  "cross_notes": "아이디어 사이의 중복·상충, 렌즈 전체 한계 3문장 이내"
}
```
32개 아이디어를 모두 판정한다(누락 금지). `refute`는 핵심 전제가 틀렸다고 입증될 때(이미 시판 중, 근거가 주장을 뒷받침하지 않음, 규제상 불가, 구조적으로 성립 불가). `weaken`은 방향은 맞지만 고쳐야 할 때. `confirm`은 반박을 시도했는데 못 무너뜨렸을 때만. rating 은 A(검증 후에도 유망), B(보완하면 가능), C(약함), X(폐기).

규칙: 읽지 않은 것을 인용하지 않는다. 수치를 계산해 새로 만들지 않는다(필요하면 '계산 가능: …'만 note). 설계값(design_value)은 근거 있는 수치로 취급하지 않는다. 쓰기 범위는 자기 출력 파일 하나. 스크래치는 `/private/tmp/claude-501/-Users-sul-Workspace-ai-studio/9ea57029-1a10-4855-9ae6-5f37dd0e11d1/scratchpad/` 아래 렌즈 이름으로 시작하는 파일만. 웹 검색은 한도가 있다(WebSearch 8회 이내, 공식 URL은 Bash curl). Tavily는 사용 한도가 차서 쓰지 않는다. 다른 프로젝트의 .env는 열지 않는다.
검증: JSON 열림, 32개 id 전부 있음, vote/rating 허용값을 python3 로 점검한다.
최종 보고: 'DONE <렌즈> confirm=N weaken=N refute=N A=N B=N C=N X=N' 한 줄과 가장 의미 있는 반증 2개.
