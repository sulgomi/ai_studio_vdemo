# 컨셉 아이디어 발굴 공통 과제

## 배경
GenZ 특화 신용카드 신상품 기획 데모다. 앞선 조사와 검증에서 확인된 것: **강한 시장 공백은 없었다.** 그래서 PM 방향은 이렇다. 새 카드는 "완전히 비어 있는 영역"이 아니어도, **CVP(혜택 구조)나 컨셉이 참신하면 된다.** 이 플랫폼이 "다음 유행"과 "새로운 관점"을 근거와 함께 제안해도 좋다. PM이 흥미로워한 방향: '졸업'·'레벨업' 컨셉, 개인 취미 발굴·배움 비용, 카드와 함께 성장하는 코스(고객이 직접 짜는 코스), 전월실적이라는 개념 자체를 다시 보기, 다음 유행(러닝·AI·한정 디저트 다음)과 연계한 카드.

## 읽을 것 (모두 `scenarios/genz-evidence/` 기준, 읽기 전용)
- `GenZ_시장브리프.md`(1차 요약과 11~13절), `whitespace_candidates.json`(검증을 거친 공백 후보 16개, 탈락 11개와 이유, 투자 판단)
- 근거 원본 `raw/*.json`: stats(ST), trends(TR), consumer(CS), wide(WT), suneung(SN), gatherings(GT), viral(VR), money(MH), invest(IV), **learning(LN), performance(PF), foresight(FS)**. 각 파일의 `facts[]`, `trend_items[]`(있으면), `cases[]`/`predictions[]`/`design_analogues[]`(있으면), `gaps[]`
- 경쟁 카드 50종 공식 페이지 기준: `competitor_db.enriched.json`(`cards[]`: name, issuer, tags, headline_benefits, annual_fee_won, min_prev_month_spend_won, on_sale, source_url). **참신하다고 말하기 전에 반드시 50종과 대조**한다.
- 규제·제도 사실: `raw/stats.json`의 policy 사실, `raw/performance.json`의 법령 사실(PFF*), `raw/invest.json`의 constraints. 이를 어기는 구조는 아이디어로 내지 않는다.

## 규칙
1. **아이디어는 가설이다.** 시장 공백이라고 주장하지 말고 "무엇이 새로운가"를 가장 비슷한 실제 카드와 대조해 쓴다. 근거는 raw 파일의 fact id(예: PFF11, LNF5)·trend id·case id로 가리킨다. 존재하지 않는 id, 읽지 않은 내용, 만든 수치를 쓰지 않는다. 계산해서 새 수치를 만들지 않는다.
2. 사실과 해석을 분리한다. 해석·제안 문장은 "해석:"으로 시작한다.
3. 참신함의 종류를 구분한다: 영역(아직 아무도 안 한 곳) | 혜택 구조 | 컨셉(이름·이야기·경험) | 실적 재해석 | 접근 방식. 영역은 비어 있지 않아도 혜택 구조나 컨셉이 새로우면 인정한다.
4. 실제 신용카드로 구현 가능해야 한다: 여전법 부가서비스 제약(혜택 유지, 경제적 이익 한도), 신용카드 현금화·금융투자상품 결제 금지, 발급 연령(만 19세, 가족카드 예외), 수익성(혜택 재원은 가맹점 수수료·연회비에 묶임), 악용(체리피킹), 개인정보를 `risks`에 사실 기반으로 쓴다. 투자 연계는 근거가 없으면 내지 않는다.
5. 구체적이어야 한다. "편리한 카드" 같은 일반론 금지. 혜택률·실적 조건·한도는 **설계값 제안**으로 쓸 수 있으나 `design_value: true`로 표시하고 근거 있는 수치처럼 쓰지 않는다.
6. 쓰기 범위: 자기 담당 출력 파일 하나(`raw/idea_<테마>.json`). 다른 파일 수정 금지. 스크래치는 `/private/tmp/claude-501/-Users-sul-Workspace-ai-studio/9ea57029-1a10-4855-9ae6-5f37dd0e11d1/scratchpad/` 아래 테마 이름으로 시작하는 파일만. 웹 검색은 한도가 있어 꼭 필요할 때만(WebSearch 5회 이내, Bash curl로 공식 URL 확인). Tavily는 사용 한도가 차서 쓰지 않는다. 다른 프로젝트의 .env는 열지 않는다.

## 출력 모양 (JSON, UTF-8, 한국어)
```json
{
  "theme": "테마", "ideas": [
    {
      "id": "<접두>I1", "name": "가칭(상품명 아님)", "one_liner": "한 문장",
      "novelty_type": ["혜택 구조", "컨셉", "실적 재해석", "영역", "접근 방식"],
      "what_is_new": "가장 비슷한 실제 카드 대비 새로운 점(카드명과 그 카드의 공식 혜택 문구를 대조)",
      "nearest_cards": [{"card": "DB 카드명", "similarity": "무엇이 비슷한가", "difference": "무엇이 다른가"}],
      "target": "누구(세분이 있으면)", "why_genz": "GenZ에게 왜 맞는가(근거 id)",
      "concept": {
        "offer": "고객이 얻는 것", "mechanism": ["작동 조건 문장 3줄 이상(대상, 적립/혜택, 조건, 한도, 고지)"],
        "performance_rule": {"type": "none | spend | behavior | tenure | goal | level | other", "description": "실적을 어떻게 다루는가"},
        "growth_path": "단계·졸업·레벨 구조가 있으면 서술, 없으면 null",
        "design_values": [{"what": "혜택률/한도/실적 등", "value": "제안값", "design_value": true}]
      },
      "evidence_ids": ["raw 파일의 fact/trend/case id"], "evidence_note": "근거가 말하는 것과 말하지 않는 것",
      "new_tags": [{"key": "snake_case", "label": "한글", "definition": "이 태그가 뜻하는 혜택 방식"}],
      "need_key": "saving|digital|social|simple|travel|fixed_cost|safety|control|invest", "domain_key": "dining|online|sub|trans|travel|daily|fixed|null",
      "platform_hook": "이 플랫폼이 이것을 제안하는 이유 한 문장(관측 근거 기반)",
      "durability": "지속 추세 | 한시 유행 | 불명",
      "risks": ["규제·수익성·악용·운영 위험(사실이면 id)"], "open_questions": ["검증단계(가상 고객·가드레일)에서 확인할 질문"],
      "interpretation_flags": ["이 아이디어에서 해석에 해당하는 부분"]
    }
  ],
  "rejected_ideas": [{"idea": "", "why": "이미 있음 | 규제 | 근거 없음 | 악용 위험"}],
  "notes": "테마 전체의 한계 2~3문장"
}
```
아이디어는 테마당 6~9개, 서로 달라야 한다. 많이 내기보다 **차별되고 근거에 닿은 것**을 낸다. 버린 아이디어도 남긴다.

## 검증
JSON 열림, evidence_ids가 raw 파일에 실재, 모든 아이디어에 nearest_cards가 1개 이상, 태그 key가 snake_case인지 python3로 점검한다.
최종 보고: 'DONE <테마> ideas=N' 한 줄과, 가장 마음에 드는 아이디어 1개의 한 줄(왜 참신한지 포함).
