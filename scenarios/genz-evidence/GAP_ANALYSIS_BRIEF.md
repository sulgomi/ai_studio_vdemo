# 시장 공백 분석 공통 과제 (deep-research 대체 실행)

## 질문
한국 GenZ(잘파·Z세대·젊은층, 만 19~29세 중심, 10대 후반~30대 초반 포함)의 2025~2026 소비·결제 트렌드를 근거로, **한국 신용카드 시장에서 아직 채워지지 않은 포인트**(미충족 니즈, 비어 있는 혜택 구조·경험·접점)가 무엇인지 찾는다. 결과는 GenZ 특화 신용카드 기획 데모의 기회영역 후보와, 그 뒤 컨셉(CVP) 작성의 씨앗이 된다. 투자 연계는 "정말 특이한 사례가 있거나 존재할 때만" 포함한다(별도 조사 `raw/invest.json`이 진행 중이면 완료 후 참고).

## 이미 모은 근거 (읽기 전용, 이 폴더 `raw/` 안)
- `stats.json`(ST: 결제·소득·제도 통계), `trends.json`(TR), `consumer.json`(CS), `wide.json`(WT: 잘파·Z세대 소비 트렌드), `suneung.json`(SN: 수능 직후·발급 연령 제도), `gatherings.json`(GT: 모임·모임통장), `viral.json`(VR: 바이럴·금융 사례), `money.json`(MH: 돈 관리·앱테크·후불결제), `invest.json`(IV: 투자 연계, 있으면)
- 모양: `sources[]`, `facts[]`(id, claim, value, population, age_scope, source_id, quote, confidence), `trend_items[]`(있는 파일만), `gaps[]`
- 경쟁 카드 50종 공식 페이지 기준: `../competitor_db.enriched.json`의 `cards[]`(name, issuer, type, tags, annual_fee_won, min_prev_month_spend_won, headline_benefits, on_sale, source_url)와 `allowed_tags`(49개 태그 키와 한글명)
- 비어 있는 방식 태그(50종에서 0종): ai_personalize, miss_refund, anti_cap, social, group_pooling, life_event, esg_green, benefit_rental. 1종: challenge, auto_best.

## 지켜야 할 규칙
1. 사실과 해석을 분리한다. 근거는 반드시 fact id(예: WTF3, GTF5, VRF12)로 가리킨다. 존재하지 않는 id, 읽지 않은 내용을 인용하지 않는다. 근거 안의 수치는 그대로 옮기고 계산해 새 수치를 만들지 않는다.
2. **"없다"는 주장은 반증을 시도한다.** 공백 후보마다 `competitor_db.enriched.json`의 50종에서 비슷한 구조를 가진 카드를 찾아 대조하고(혜택 문구까지 읽는다), 가능하면 웹 검색(WebSearch/WebFetch, curl)으로 DB 밖의 시판 카드도 확인한다. 검색이 막히면 DB만으로 판정하고 `search_available: false`로 적는다. 판정은 none(비슷한 것 없음) | partial(일부만 하는 곳 있음) | exists(이미 있음).
3. age_scope를 지킨다. 근거가 20대가 아니라 MZ·전연령이면 후보에 그 한계를 쓴다.
4. 홍보성 글(tier D, promotional)은 수치 근거로 쓰지 않는다. stale 근거만으로 선 후보는 strength를 낮춘다.
5. 카드로 풀 수 있는 것만 후보로 삼는다. 후보는 구체적이어야 한다("편리한 카드" 같은 일반론 금지). 혜택 구조/경험/접점/조건/제휴 중 무엇이 비어 있는지 특정한다.
6. 쓰기 범위: 자기 담당 출력 파일 하나(`raw/gap_<각도>.json`). 다른 파일, 스키마, 설계서, 기존 시나리오 폴더 수정 금지. 스크래치는 `/private/tmp/claude-501/-Users-sul-Workspace-ai-studio/9ea57029-1a10-4855-9ae6-5f37dd0e11d1/scratchpad/` 아래 자기 각도 이름으로 시작하는 파일만.

## 출력 모양 (JSON, UTF-8, 한국어)
```json
{
  "angle": "각도 이름",
  "search_available": true,
  "candidates": [
    {
      "id": "<각도접두>C1",
      "title": "공백 후보 한 줄(무엇이 비어 있나)",
      "gap_type": "benefit_structure | experience | touchpoint | condition | partnership | trust",
      "unmet_need": "고객이 못 얻는 것(사실 기반 서술, 해석은 '해석:'으로 시작)",
      "genz_basis": [{"fact_id": "WTF3", "says": "그 fact가 말하는 것 한 문장", "age_scope": "", "weight": "핵심 | 보조"}],
      "existing_check": {
        "db_cards_compared": ["카드명 ..."],
        "similar": [{"card": "", "how_similar": "공식 혜택 문구 기준", "difference": ""}],
        "web_checked": ["확인한 DB 밖 카드/서비스와 결과"],
        "verdict": "none | partial | exists",
        "note": ""
      },
      "mechanism_tags": ["allowed_tags 키 1~2개"],
      "need_key": "saving|digital|social|simple|travel|fixed_cost|safety|invest",
      "domain_key": "dining|online|sub|trans|travel|daily|fixed|null",
      "strength": "강 | 중 | 약",
      "strength_reason": "근거의 두께(출처 수, 20대 특정성, 최신성) 한두 문장",
      "counter_evidence": "반대 증거나 이 후보가 틀릴 수 있는 이유",
      "risks": ["규제·수익성·체리피킹·운영상 위험(사실이면 fact id)"],
      "invest_related": false,
      "cvp_seed": {
        "target": "누구", "offer": "무엇을 주는가(구조)", "key_benefit": "핵심 효익",
        "alternative": "지금 고객이 쓰는 대안(실제 카드/서비스 이름)",
        "differentiator": "가장 비슷한 실제 카드와 무엇이 다른가",
        "reason_to_believe": ["fact id 또는 '가정'"]
      }
    }
  ],
  "rejected": [{"idea": "검토했지만 버린 후보", "why": "이미 존재 | 근거 약함 | 카드로 못 풀음 | 규제"}],
  "notes": "각도 전체에 대한 한계 2~3문장"
}
```
후보는 각도당 4~7개. 많이 내기보다 **근거와 반증이 확실한 것**을 낸다. 버린 후보(rejected)도 남긴다.

## 검증
JSON 열림, 모든 fact_id가 raw 파일들에 실재, 모든 후보에 existing_check.verdict 있음, mechanism_tags가 allowed_tags 키인지 python3로 점검한다.
최종 보고: 'DONE <각도> candidates=N none=N partial=N exists=N' 한 줄과 가장 강한 후보 1개의 한 줄 요약, 막힌 것.
