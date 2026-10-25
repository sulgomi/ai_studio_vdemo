# 공백 후보 적대적 검증 공통 과제

`raw/gap_touchpoint.json`, `gap_social.json`, `gap_control.json`, `gap_entry.json`, `gap_viral.json`(각 `candidates[]`, 총 31개)은 "GenZ 특화 신용카드 시장에서 아직 채워지지 않은 포인트" 후보다. 후보 작성자는 자기 후보를 지지하는 쪽으로 쓰기 쉽다. 당신은 **반박하는 검증자**다. 후보를 살리려 하지 말고, 무너뜨릴 수 있는지 먼저 시도한다. 근거 없이 지지하지도, 근거 없이 반박하지도 않는다.

읽을 것(이 폴더 `scenarios/genz-evidence/` 기준): `GAP_ANALYSIS_BRIEF.md`(후보 모양과 규칙), 위 gap 파일 5개, 근거 raw(`stats.json`, `trends.json`, `consumer.json`, `wide.json`, `suneung.json`, `gatherings.json`, `viral.json`, `money.json`, 있으면 `invest.json`), `competitor_db.enriched.json`(경쟁 카드 50종).

## 출력 (`raw/verify_<렌즈>.json`, UTF-8, 한국어)
```json
{
  "lens": "렌즈 이름",
  "search_available": true,
  "checks": [
    {"candidate_id": "TPC1", "vote": "confirm | weaken | refute",
     "findings": ["확인한 사실·반증. 근거 fact id나 URL(읽은 것만)"],
     "corrections": ["후보 서술에서 고쳐야 할 점(과장된 표현, 잘못 읽은 근거, 놓친 기존 카드 등)"],
     "adjusted_strength": "강 | 중 | 약 | 폐기",
     "confidence_in_vote": "high | medium | low"}
  ],
  "cross_notes": "후보들 사이의 중복·상충, 렌즈 전체 한계 3문장 이내"
}
```
31개 후보를 모두 판정한다(누락 금지). `refute`는 후보의 핵심 전제가 틀렸다고 입증될 때만(예: 이미 시판 중, 근거가 후보 주장을 뒷받침하지 않음, 규제상 불가). `weaken`은 방향은 맞지만 강도를 낮춰야 할 때. `confirm`은 반박을 시도했는데 못 무너뜨렸을 때만. 판정마다 어떤 반박을 시도했는지 findings에 쓴다.

규칙: 읽지 않은 것을 인용하지 않는다. 수치를 계산해 새로 만들지 않는다. 쓰기 범위는 자기 출력 파일 하나. 스크래치는 `/private/tmp/claude-501/-Users-sul-Workspace-ai-studio/9ea57029-1a10-4855-9ae6-5f37dd0e11d1/scratchpad/` 아래 렌즈 이름으로 시작하는 파일만.
검증: JSON 열림, 31개 후보 id 전부 있음, vote 값이 허용값인지 python3로 점검한다.
최종 보고: 'DONE <렌즈> confirm=N weaken=N refute=N' 한 줄과 가장 의미 있는 반증 2개.
