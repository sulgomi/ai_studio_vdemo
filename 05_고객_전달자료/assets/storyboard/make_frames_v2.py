"""고객 제안용 스토리보드 와이어프레임(SVG) 생성.

실행: python3 make_frames_v2.py  → v2/A-01.svg ~ A-11.svg (안 A), v2/B-01.svg ~ B-10.svg (안 B)
make_frames.py의 도형 함수를 재사용한다. 화면 구성은 ui/user-view.html을 단순화한 것이다.
"""
from pathlib import Path

_src = (Path(__file__).parent / "make_frames.py").read_text(encoding="utf-8").split("for i, fn in enumerate([s01")[0]
exec(compile(_src, "make_frames.py", "exec"))

OUT2 = Path(__file__).parent / "v2"
OUT2.mkdir(exist_ok=True)
NO = [1]
_frame = frame
def frame(no, title, body, caption):  # 번호는 NO[0]로 덮어쓴다
    return _frame(NO[0], title, body, caption)

TEAL = "#0e8f80"


def agent_node(x, y, w, label, sub="", fill=LIGHT, stroke=BLUE, dashed=False):
    s = box(x, y, w, 52, fill=fill, stroke=stroke, dash="5 3" if dashed else None, sw=1.5)
    s += t(x + w / 2, y + 22, label, 13, NAVY, 700, "middle")
    if sub:
        s += t(x + w / 2, y + 41, sub, 11, GRAY, 400, "middle")
    return s


def msg(x, y, w, text, color=BLUE):
    return box(x, y, w, 30, fill="#fff", stroke=color, r=15) + t(x + w / 2, y + 20, text, 11, color, 600, "middle")



# ---------- 통합 보고서 목업 (대표 이미지가 제목과 함께 맨 위) ----------
def report_mock(x, y, name, hook, portrait, facts, mode_label="기획보고서 (HTML)"):
    b = box(x, y, 376, 400, fill="#fff", stroke=BLUE)
    b += f'<rect x="{x}" y="{y}" width="376" height="26" rx="8" fill="{LIGHT}"/>' + t(x + 12, y + 18, mode_label, 11, NAVY, 700)
    b += box(x + 250, y + 5, 58, 16, r=5) + t(x + 279, y + 17, "HTML 저장", 9, NAVY, 600, "middle") + box(x + 314, y + 5, 50, 16, r=5) + t(x + 339, y + 17, "인쇄·PDF", 9, NAVY, 600, "middle")
    b += f'<rect x="{x + 10}" y="{y + 34}" width="356" height="150" rx="8" fill="#14141a"/>'
    b += t(x + 22, y + 54, "NEW PRODUCT PLANNING REPORT", 8, "#cfd3e6", 700)
    b += t(x + 22, y + 92, name, 26, "#fff", 800) + t(x + 22 + len(name) * 24 + 4, y + 92, ".", 26, "#d6ff3f", 800)
    b += t(x + 22, y + 116, hook[0], 10, "#d7d9e6") + t(x + 22, y + 130, hook[1], 10, "#d7d9e6")
    if portrait:
        for (dx, dy, rot, col, w, h) in [(222, 56, -9, "#E4DDCB", 40, 62), (262, 50, 9, "#23305C", 40, 62), (242, 44, 0, "#C8F25A", 44, 70)]:
            b += f'<g transform="rotate({rot} {x + dx + w / 2} {y + 34 + dy + h / 2})"><rect x="{x + dx}" y="{y + 34 + dy}" width="{w}" height="{h}" rx="6" fill="{col}" stroke="#fff" stroke-opacity="0.6"/><rect x="{x + dx + 6}" y="{y + 34 + dy + 8}" width="10" height="8" rx="2" fill="#C9A24A"/></g>'
    else:
        for (dx, dy, rot, col, w, h) in [(212, 62, -8, "#1F3A5F", 66, 42), (270, 58, 8, "#F7EBD3", 66, 42), (240, 44, 0, "#ffffff", 76, 48)]:
            b += f'<g transform="rotate({rot} {x + dx + w / 2} {y + 34 + dy + h / 2})"><rect x="{x + dx}" y="{y + 34 + dy}" width="{w}" height="{h}" rx="6" fill="{col}" stroke="#fff" stroke-opacity="0.6"/><rect x="{x + dx + 6}" y="{y + 34 + dy + 8}" width="12" height="9" rx="2" fill="#C9A24A"/></g>'
    for i, (k, v) in enumerate(facts):
        fx = x + 10 + i * 120
        b += box(fx, y + 194, 116, 40, fill="#fafbff", stroke=LINE, r=6) + t(fx + 8, y + 208, k, 8, GRAY, 700) + t(fx + 8, y + 226, v, 11, NAVY, 700)
    secs = ["00 핵심 요약", "01 시장과 기회", "02 상품 컨셉", "03 시장성", "04 브랜드·디자인·마케팅", "05 리스크·확인 사항", "06 의사결정 요청", "A 부록"]
    for i, sname in enumerate(secs):
        cx = x + 12 + (i % 2) * 180
        cy = y + 248 + (i // 2) * 24
        b += t(cx, cy + 12, sname, 11, BLUE if i == 4 else NAVY, 700 if i == 4 else 400)
    b += box(x + 10, y + 350, 356, 40, fill=LIGHT, stroke=LIGHT, r=6) + t(x + 20, y + 366, "6개 에이전트 결과를 주제별로 통합 · 원자료는 부록", 10, NAVY, 600) + t(x + 20, y + 381, "시장조사 · 시장기회 · 컨셉 · 시장성 · 가드레일 · 디자인·마케팅", 9, GRAY)
    return b


def report_chat(center_text, fn_name):
    def c(x, y, w):
        s = bubble(x + 20, y + 20, w - 40, "최종 요약해서 신상품기획보고서로 만들어줘", me=True)
        s += box(x + 20, y + 70, w - 40, 150, fill=LIGHT)
        s += t(x + 34, y + 94, "최종 요약", 12, GRAY, 700) + t(x + 34, y + 118, fn_name, 14, NAVY, 700)
        for i, line in enumerate(center_text):
            s += t(x + 34, y + 142 + i * 22, line, 12)
        s += box(x + 20, y + 240, 140, 32, fill=BLUE, stroke=BLUE, r=6) + t(x + 90, y + 261, "보고서로 보기", 12, "#fff", 600, "middle")
        return s
    return c

# ============ 안 A: 2030 투자입문자 ============

def a01():
    body = (t(W / 2, 170, "카드 신상품 하나를 기획하려면", 22, GRAY, 400, "middle")
            + t(W / 2, 210, "시장조사 · 경쟁 분석 · 컨셉 · 검증 · 디자인 · 기획서", 18, NAVY, 600, "middle"))
    xs = [150, 270, 390, 510, 630, 750]
    for i, x in enumerate(xs):
        body += box(x - 20, 250, 100, 60, fill=LIGHT) + t(x + 30, 285, ["조사", "경쟁", "컨셉", "검증", "디자인", "기획서"][i], 13, NAVY, 600, "middle")
        if i < 5:
            body += arrow(x + 80, 280, x + 100, 280)
    body += t(W / 2, 360, "AI 에이전트 팀이 협의하며 수행, 사람은 핵심 지점에서 결정", 16, BLUE, 600, "middle")
    return frame(1, "오프닝", body, "카드 상품기획 전 과정을 에이전트 팀이 분담")


def a02():
    def c(x, y, w):
        s = bubble(x + 20, y + 20, w - 40, "2030 투자 입문자를 위한 새로운 신용카드를 기획해줘", me=True)
        s += log_line(x + 20, y + 80, "intake", "타깃·카드 유형 해석")
        s += box(x + 20, y + 100, w - 40, 150, fill="#fff", stroke=BLUE)
        s += t(x + 36, y + 124, "범위 확인", 13, BLUE, 700)
        rows = [("타깃", "2030 투자입문자"), ("카드 유형", "신용카드"), ("가정", "고객 데이터 없이 공개 자료 사용")]
        for i, (k, v) in enumerate(rows):
            s += t(x + 36, y + 154 + i * 26, k, 12, GRAY) + t(x + 150, y + 154 + i * 26, v, 12)
        s += box(x + w - 200, y + 266, 80, 30, fill=BLUE, stroke=BLUE, r=6) + t(x + w - 160, y + 286, "확인", 12, "#fff", 600, "middle")
        s += box(x + w - 110, y + 266, 70, 30, r=6) + t(x + w - 75, y + 286, "수정", 12, NAVY, 600, "middle")
        return s
    return frame(2, "사용자 뷰 · 상품기획", user_layout(c), "요청 한 줄 입력 → AI의 범위 해석 → 사람 확인")


def a05():
    body = box(32, 56, 896, 400, fill="#fff")
    opts = [("잔돈씨앗 카드", "제휴 구조"), ("같이굴려요 카드", "고객 경험"), ("놓친적립 되돌림 카드", "혜택 구조")]
    for i, (n, lv) in enumerate(opts):
        x = 60 + i * 200
        win = i == 1
        body += box(x, 80, 180, 90, fill="#f3f7ff" if win else "#fff", stroke=BLUE if win else LINE, sw=2 if win else 1)
        body += t(x + 90, 112, n, 13, NAVY, 700, "middle") + t(x + 90, 136, f"바꾼 축: {lv}", 11, GRAY, 400, "middle")
        body += t(x + 90, 158, "승자" if win else "코드 평가", 11, OK if win else GRAY, 600, "middle")
    body += arrow(660, 125, 690, 125)
    body += box(700, 80, 200, 90, fill=LIGHT) + t(800, 108, "코드 평가", 13, NAVY, 700, "middle") + t(800, 130, "손익 · 유사도 · 복잡도", 11, GRAY, 400, "middle") + t(800, 150, "특별한 포인트 · 금칙어", 11, GRAY, 400, "middle")
    body += t(60, 210, "시장성 검증 · 가상 고객 1,760명", 14, NAVY, 700)
    bars = [("기본", 0.396), ("경쟁사 모방", 0.281), ("혜택 20% 축소", 0.376), ("시장 위축", 0.333)]
    for i, (n, v) in enumerate(bars):
        yy = 232 + i * 36
        body += t(60, yy + 16, n, 12, GRAY) + box(170, yy + 2, 300, 20, fill=LIGHT, stroke=LIGHT, r=4)
        body += box(170, yy + 2, 300 * v / 0.5, 20, fill=BLUE if i == 0 else "#9fb3ff", stroke="none", r=4)
        body += t(170 + 300 * v / 0.5 + 8, yy + 17, f"{v * 100:.1f}%", 12, NAVY, 600)
    body += t(60, 392, "채택 의향: 가정을 바꿔 가며 비교", 11, GRAY)
    body += box(560, 210, 340, 160, fill="#fafbff")
    body += t(576, 234, "체리피커 반응", 12, WARN, 700)
    body += t(576, 258, "\"외식이랑 온라인만 이 카드로 긁고", 12) + t(576, 278, "나머지는 다른 카드로 돌릴게요.\"", 12)
    body += t(576, 310, "일반형 58% · 체리피커 21% · 휴면 위험형 15%", 11, GRAY)
    body += t(576, 352, "가상 고객 시뮬레이션(가정 기반) · 실제 전환율 아님", 11, BAD, 600)
    return frame(5, "사용자 뷰 · 상품기획", body, "컨셉 3안 코드 평가, 가상 고객 시뮬레이션으로 시장성 확인")


def a06():
    body = box(32, 56, 896, 400, fill="#fff")
    body += t(60, 88, "에이전트 간 협의 · 컨셉 보완", 15, NAVY, 700)
    body += agent_node(60, 120, 200, "06 컨셉", "3안 중 같이굴려요 승자")
    body += agent_node(380, 120, 200, "07 시장성 검증", "가상 고객 1,760명")
    body += agent_node(700, 120, 200, "08 가드레일 (선택)", "재무·준법 의견", fill="#fff", stroke=GRAY, dashed=True)
    body += arrow(260, 136, 380, 136, BLUE) + arrow(380, 156, 260, 156, BLUE)
    body += arrow(580, 146, 700, 146, GRAY)
    body += msg(60, 200, 250, "컨셉 3안과 코드 평가 결과 전달")
    body += msg(330, 200, 250, "경쟁사 모방 시 28.1%, 체리피커 반응 전달", OK)
    body += msg(620, 200, 280, "이름이 투자 수익을 연상시킨다는 의견", GRAY)
    body += box(60, 258, 840, 80, fill=LIGHT)
    body += t(80, 284, "협의 쟁점", 12, GRAY, 700)
    body += t(80, 310, "‘같이굴려요’ 이름이 실제 구조(모임 합산 적립)보다 강한 인상. 필요 시에만 가드레일이 의견 추가", 12)
    body += box(60, 352, 840, 90, fill="#fff", stroke=OK)
    body += box(80, 372, 170, 44, fill="#fff", stroke=BAD) + t(165, 400, "같이굴려요 카드", 13, BAD, 700, "middle")
    body += arrow(250, 394, 330, 394, BLUE) + t(290, 386, "컨셉 재작업", 10, BLUE, 600, "middle")
    body += box(340, 372, 170, 44, fill="#fff", stroke=OK, sw=2) + t(425, 400, "함께쌓기 카드", 13, OK, 700, "middle")
    body += t(540, 392, "협의 결과로 이름이 바뀜", 13, NAVY, 600) + t(540, 414, "변경 이력은 기획서 부록에 남음", 12, GRAY)
    return frame(6, "사용자 뷰 · 에이전트 협의", body, "에이전트 간 결과 교환으로 컨셉 보완, 가드레일은 필요 시에만 추가")


def a08():
    c = report_chat(["컨셉·시장성·브랜드·리스크를 한 문서로 통합", "법무 확인 필요 항목 표시", "의사결정 요청 5건"], "함께쌓기 카드")
    r = lambda x, y: report_mock(x, y, "함께쌓기 카드", ("모임 챌린지를 채우면 적립 포인트 일부와", "한도 내 보너스가 각자 몫으로 쌓이는 카드"), False, [("타깃", "2030 투자 입문자"), ("주요 혜택", "모임 챌린지 보너스"), ("차별점", "모임 단위 투자 연계")])
    return frame(8, "사용자 뷰 · 신상품기획보고서", user_layout(c, r), "6개 에이전트 결과를 하나의 신상품기획보고서로 통합")


def a09():
    def c(x, y, w):
        s = bubble(x + 20, y + 16, w - 40, "시판 카드 34종 중 어디가 붐비고 어디가 비어 있는지 알려줘", me=True)
        s += box(x + 20, y + 64, w - 40, 74, fill="#f3f7ff", stroke=BLUE)
        s += t(x + 34, y + 86, "오케스트레이터", 12, BLUE, 700)
        s += t(x + 34, y + 108, "입력 분석: 경쟁사 시장 구조 질문", 12) + t(x + 34, y + 126, "→ 03 경쟁사 에이전트 호출", 12, BLUE, 600)
        s += box(x + 20, y + 152, w - 40, 134, fill=LIGHT)
        s += t(x + 34, y + 174, "03 경쟁사", 12, GRAY, 700)
        s += t(x + 34, y + 198, "붐비는 혜택: 청구할인형 15 · 해외결제 14 · 외식·카페 12", 12)
        s += t(x + 34, y + 222, "비어 있는 혜택: 투자 리워드 0종 / 34종", 12, WARN, 600)
        s += t(x + 34, y + 246, "가까운 카드: ZERO Edition3 · 현대카드 M · LOCA LIKIT 1.2", 12)
        s += t(x + 34, y + 270, "집계는 코드, 해석은 AI", 11, GRAY)
        return s
    return frame(9, "개별 에이전트 활용 · 담당 에이전트 호출", user_layout(c, history=("경쟁사 구조 질문", "2030 투자 입문자 카드")), "질문을 분석해 맞는 전문 에이전트를 오케스트레이터가 불러옵니다")


def a10():
    body = box(32, 56, 896, 400, fill="#fff")
    body += t(60, 88, "타 전문 영역이 필요하면 에이전트를 함께 호출해 협의", 15, NAVY, 700)
    body += box(60, 108, 840, 52, fill="#f3f7ff", stroke=BLUE)
    body += t(76, 130, "오케스트레이터", 12, BLUE, 700) + t(76, 150, "경쟁사 결과만으로는 타깃 니즈를 판단할 수 없음 → 04 소비자, 02 트렌드를 함께 호출", 12)
    body += agent_node(60, 190, 240, "03 경쟁사", "투자 리워드 0종 / 34종")
    body += agent_node(360, 190, 240, "04 소비자", "투자 연계 니즈 1순위")
    body += agent_node(660, 190, 240, "02 트렌드", "연계 선례, 신뢰도 0.6")
    body += arrow(300, 216, 360, 216, BLUE) + arrow(360, 226, 300, 226, BLUE) + arrow(600, 216, 660, 216, BLUE) + arrow(660, 226, 600, 226, BLUE)
    body += chip(110, 254, "빈칸", WARN, 60) + chip(410, 254, "니즈 1순위", OK, 110) + chip(700, 254, "증권사 연계 선례", BAD, 150)
    body += box(60, 296, 840, 90, fill=LIGHT)
    body += t(80, 322, "종합 의견 (의사결정 지원)", 12, GRAY, 700)
    body += t(80, 348, "투자 연계는 니즈 1순위이자 시판 카드의 빈칸이지만,", 14, NAVY, 600)
    body += t(80, 370, "증권사 연계 선례 존재, 차별화와 제휴 확보가 관건", 14, NAVY, 600)
    body += box(60, 398, 840, 40, fill="#fff", stroke=OK) + t(80, 423, "최종 판단은 사람이 수행, 에이전트는 근거와 쟁점을 정리", 12, OK, 600)
    return frame(10, "개별 에이전트 활용 · 에이전트 협의", body, "필요하면 다른 전문가 에이전트를 함께 불러 의견을 모아 드립니다")


# ============ 안 B: GenZ ============

def b01():
    def c(x, y, w):
        s = bubble(x + 20, y + 20, w - 40, "GenZ 특화 신용카드 만들어줘", me=True)
        s += log_line(x + 20, y + 80, "intake", "GenZ → 만 19~29세로 해석")
        s += box(x + 20, y + 100, w - 40, 170, fill="#fff", stroke=BLUE)
        s += t(x + 36, y + 124, "범위 확인", 13, BLUE, 700)
        rows = [("타깃", "GenZ (만 19~29세)"), ("카드 유형", "신용카드"), ("범위", "투자 연계 제외"), ("가정", "고객 데이터 없이 공개 자료 사용")]
        for i, (k, v) in enumerate(rows):
            s += t(x + 36, y + 154 + i * 26, k, 12, GRAY) + t(x + 150, y + 154 + i * 26, v, 12)
        s += box(x + w - 200, y + 286, 80, 30, fill=BLUE, stroke=BLUE, r=6) + t(x + w - 160, y + 306, "확인", 12, "#fff", 600, "middle")
        s += box(x + w - 110, y + 286, 70, 30, r=6) + t(x + w - 75, y + 306, "수정", 12, NAVY, 600, "middle")
        return s
    return frame(1, "사용자 뷰 · 상품기획", user_layout(c, history=("GenZ 특화 신용카드",)), "GenZ를 만 19~29세로 해석, 사람이 범위 확인")


def b02():
    body = box(32, 56, 896, 400, fill="#fff")
    body += box(390, 74, 180, 46, fill=NAVY, stroke=NAVY) + t(480, 103, "01 시장조사 총괄", 14, "#fff", 700, "middle")
    body += arrow(420, 120, 200, 168, BLUE) + arrow(540, 120, 580, 168, BLUE)
    body += box(110, 168, 180, 52, fill=LIGHT, stroke=BLUE) + t(200, 192, "02 트렌드", 13, NAVY, 700, "middle") + t(200, 211, "신호 5개 · 웹 검색", 11, GRAY, 400, "middle")
    body += box(490, 168, 180, 52, fill=LIGHT, stroke=BLUE) + t(580, 192, "03 경쟁사", 13, NAVY, 700, "middle") + t(580, 211, "시판 34종 집계", 11, GRAY, 400, "middle")
    body += chip(150, 226, "동시 실행", OK, 80) + chip(530, 226, "동시 실행", OK, 80)
    body += arrow(200, 256, 440, 274, BLUE) + arrow(580, 256, 520, 274, BLUE)
    body += box(380, 274, 200, 40, fill=LIGHT, stroke=BLUE) + t(480, 300, "04 소비자 (이어서)", 13, NAVY, 700, "middle")
    body += box(60, 326, 840, 124, fill="#fafbff")
    body += t(76, 348, "종합 결론", 12, GRAY, 600)
    body += t(76, 372, "공백 혜택과 디지털·절약 니즈는 부합하나, 혜택 불신이", 14, NAVY, 600) + t(76, 394, "발급 동기를 약화", 14, NAVY, 600)
    body += chip(76, 414, "간편결제 일평균 1조464억원", BLUE, 190) + chip(276, 414, "환급·실적조건 완화 0종 / 34종", WARN, 210) + chip(496, 414, "출처 11건", BLUE, 90) + chip(596, 414, "충돌 3건 나란히", BAD, 120)
    return frame(2, "사용자 뷰 · 시장조사", body, "에이전트들이 조사하고, 엇갈린 근거는 합치지 않고 나란히 보여 줍니다")


def b03():
    def c(x, y, w):
        s = t(x + 20, y + 30, "기회 선택: 컨셉으로 넘길 기회를 골라 주세요", 13, BLUE, 700)
        cards = [("1순위", "GenZ × 구독·디지털", "천장 0.56 · 근거 T2", True),
                 ("2순위", "GenZ × 단순함", "천장 0.68 · 실적조건 완화 0종", False),
                 ("3순위", "GenZ × 소셜", "천장 0.56", False)]
        for i, (r, n, sub, sel) in enumerate(cards):
            yy = y + 50 + i * 100
            s += box(x + 20, yy, w - 40, 86, fill="#f3f7ff" if sel else "#fff", stroke=BLUE if sel else LINE, sw=2 if sel else 1)
            s += t(x + 36, yy + 26, r, 12, GRAY, 600) + t(x + 96, yy + 26, n, 14, NAVY, 700)
            s += t(x + 96, yy + 50, sub, 12, GRAY)
            s += t(x + 96, yy + 70, "시장 천장(도달 가능한 규모)을 코드가 먼저 점검", 11, OK)
            if sel:
                s += box(x + w - 110, yy + 28, 70, 30, fill=BLUE, stroke=BLUE, r=6) + t(x + w - 75, yy + 48, "선택", 12, "#fff", 600, "middle")
        return s
    return frame(3, "사용자 뷰 · 상품기획", user_layout(c, history=("GenZ 특화 신용카드",)), "점수·현실성은 코드가 계산, 기회 선택은 사람이 결정")


def b04():
    body = box(32, 56, 896, 400, fill="#fff")
    body += t(60, 88, "컨셉 3안과 코드 평가 (모두 가칭)", 15, NAVY, 700)
    rows = [("알아서 맞춤 캐시백 카드", "혜택 구조", "38.3%", "승자", OK), ("첫 신용 단계 카드", "타깃 세분", "30.3%", "기준 미달 탈락", BAD), ("함께 채우는 실적 카드", "고객 경험", "40.5%", "통과", GRAY)]
    for i, (n, lv, v, st, col) in enumerate(rows):
        x = 60 + i * 290
        win = i == 0
        body += box(x, 108, 270, 120, fill="#f3f7ff" if win else "#fff", stroke=BLUE if win else LINE, sw=2 if win else 1)
        body += t(x + 135, 138, n, 13, NAVY, 700, "middle") + t(x + 135, 160, f"바꾼 축: {lv}", 11, GRAY, 400, "middle")
        body += t(x + 135, 190, f"채택 의향 {v}", 13, NAVY, 600, "middle") + chip(x + 85, 198, st, col, 100)
    body += t(60, 262, "코드 평가 항목", 13, NAVY, 700)
    for i, (k, v) in enumerate([("손익", "정적 · 채택 고객 기준"), ("경쟁 카드 유사도", "가장 가까운 카드와 비교"), ("복잡도", "고객이 이해할 수 있는 수준"), ("체리피커 비중", "승자 안 45.0%")]):
        body += box(60 + i * 215, 276, 200, 70, fill=LIGHT, stroke=LIGHT) + t(160 + i * 215, 304, k, 12, NAVY, 700, "middle") + t(160 + i * 215, 326, v, 11, GRAY, 400, "middle")
    body += t(60, 384, "가상 고객 시뮬레이션(가정 기반) · 실제 전환율 아님", 12, BAD, 600)
    body += t(60, 412, "수치는 코드가 계산, 고객 반응 해석은 AI가 수행", 12, GRAY)
    return frame(4, "사용자 뷰 · 컨셉 평가", body, "서로 다른 컨셉 3안을 코드가 평가해 한 안을 떨어뜨립니다")


def b05():
    body = box(32, 56, 896, 400, fill="#fff")
    body += t(60, 88, "에이전트 간 협의 · 컨셉 보완", 15, NAVY, 700)
    body += agent_node(60, 120, 200, "06 컨셉", "알아서 맞춤 캐시백 승자")
    body += agent_node(380, 120, 200, "07 시장성 검증", "채택 의향 38.3%")
    body += agent_node(700, 120, 200, "08 가드레일 (선택)", "재무·준법 의견", fill="#fff", stroke=GRAY, dashed=True)
    body += arrow(260, 136, 380, 136, BLUE) + arrow(380, 156, 260, 156, BLUE) + arrow(580, 146, 700, 146, GRAY)
    body += msg(60, 200, 250, "컨셉 3안과 코드 평가 전달")
    body += msg(330, 200, 250, "체리피커 채택자 45.0% 전달", OK)
    body += msg(620, 200, 280, "이름이 AI 개인화처럼 읽힌다는 의견", GRAY)
    body += box(60, 258, 840, 110, fill=LIGHT)
    body += t(80, 284, "협의 쟁점 3가지", 12, GRAY, 700)
    body += t(80, 312, "1. ‘알아서 맞춤’이라는 이름이 실제 작동보다 강하게 읽힘", 13, NAVY, 600)
    body += t(80, 336, "2. 혜택 문구가 오인될 수 있음", 13, NAVY, 600)
    body += t(80, 360, "3. 체리피킹 비중을 유지할지는 재무가 정할 사항", 13, NAVY, 600)
    body += box(60, 384, 840, 56, fill="#fff", stroke=BLUE) + t(80, 418, "→ 컨셉 에이전트가 쟁점을 반영해 재설계, 가드레일은 필요 시에만 참여", 12, BLUE, 600)
    return frame(5, "사용자 뷰 · 에이전트 협의", body, "에이전트 간 쟁점 교환을 거쳐 컨셉 재설계")


def b06():
    body = box(32, 56, 896, 400, fill="#fff")
    body += t(60, 88, "협의 결과 · 바뀐 점", 15, NAVY, 700)
    body += t(250, 122, "협의 전", 12, GRAY, 700, "middle") + t(640, 122, "협의 후", 12, OK, 700, "middle")
    rows = [("이름", "알아서 맞춤 캐시백 카드", "많이 쓴 영역 캐시백 카드"), ("1위 영역 판정", "그 달 결제 내역", "직전 3개월 합계"), ("채택 의향", "38.3%", "41.2%")]
    for i, (k, a, b) in enumerate(rows):
        yy = 140 + i * 60
        body += t(60, yy + 30, k, 12, GRAY, 700)
        body += box(170, yy, 240, 40, fill="#fff5f5", stroke=BAD) + t(290, yy + 26, a, 12, NAVY, 600, "middle")
        body += arrow(410, yy + 20, 470, yy + 20, BLUE)
        body += box(480, yy, 250, 40, fill="#f4fbf7", stroke=OK, sw=2) + t(605, yy + 26, b, 12, NAVY, 700, "middle")
    body += box(60, 352, 840, 90, fill=LIGHT)
    body += t(80, 378, "남은 항목은 숨기지 않고 담당 부서 확인으로 넘깁니다", 13, NAVY, 700)
    body += t(80, 402, "환급은 연 1회로 정리. 문구 보완, 체리피킹 비중(재무 결정), 부가서비스 변경 고지·개인정보는 사람 확인", 12, GRAY)
    body += t(80, 426, "채택 의향은 가상 고객 시뮬레이션(가정 기반) 값", 11, BAD, 600)
    return frame(6, "사용자 뷰 · 협의 결과", body, "협의 결과가 이름·규칙에 반영, 미해결 항목은 공개")


def b07():
    body = box(32, 56, 896, 400, fill="#fff")
    body += t(60, 88, "근거가 부족하면 다시 조사 요청", 15, NAVY, 700)
    body += agent_node(60, 112, 250, "09 디자인·마케팅", "이름 ‘세칸’ · 시안 NOON/CLEAR/NIGHT")
    body += agent_node(610, 112, 250, "02 트렌드", "근거 팩 재조사")
    body += arrow(310, 128, 610, 128, BLUE) + arrow(610, 148, 310, 148, BLUE)
    body += msg(340, 86, 240, "근거 부족 3주제 재조사 요청", WARN) + msg(340, 160, 240, "약한 근거 보강 · 못 찾은 것은 표시", OK)
    for i, (n, col) in enumerate([("NOON", "#f3d9a6"), ("CLEAR", "#e8eef6"), ("NIGHT", "#24345e")]):
        x = 60 + i * 150
        body += f'<rect x="{x}" y="196" width="120" height="150" rx="10" fill="{col}" stroke="{LINE}"/>'
        body += t(x + 60, 330, n, 12, "#fff" if i == 2 else NAVY, 700, "middle")
    body += t(60, 366, "세로형 카드 시안 3종", 11, GRAY)
    body += box(520, 196, 380, 170, fill="#fafbff")
    body += t(536, 220, "재조사 결과", 12, GRAY, 700)
    body += t(536, 246, "간편결제 등록 안내: 근거 확보", 12) + chip(780, 232, "T7", OK, 50)
    body += t(536, 276, "숏폼 시험 집행: 약한 근거", 12) + chip(780, 262, "0.45", WARN, 60)
    body += t(536, 306, "20대 연령별 수치: 근거 없음", 12) + chip(780, 292, "없음", BAD, 60)
    body += t(536, 346, "찾지 못한 것은 ‘근거 없음’으로 남깁니다", 11, BAD, 600)
    body += box(60, 392, 840, 48, fill="#fff", stroke=BLUE) + t(80, 422, "영상은 사람 확정 후 렌더, 이번 회차는 스토리보드(릴스·유튜브·홍보)로 대체", 12, BLUE, 600)
    return frame(7, "사용자 뷰 · 디자인·마케팅", body, "근거 부족 시 타 에이전트에 재조사 요청, 없는 근거는 ‘근거 없음’으로 표기")


def b08():
    c = report_chat(["컨셉·시장성·브랜드·리스크를 한 문서로 통합", "결정 요청과 추가 조사 주제 정리", "채택 의향은 가정 기반 값"], "세칸")
    r = lambda x, y: report_mock(x, y, "세칸", ("직전 3개월 합계 1위 영역에", "캐시백이 자동 배정되는 카드"), True, [("타깃", "만 19~29세 GenZ"), ("주요 혜택", "1위 영역 1.3%"), ("차별점", "영역 자동 배정")])
    return frame(8, "사용자 뷰 · 신상품기획보고서", user_layout(c, r, history=("GenZ 특화 신용카드",)), "6개 에이전트 결과를 하나의 신상품기획보고서로 통합")


def b09():
    def c(x, y, w):
        s = bubble(x + 20, y + 16, w - 40, "GenZ 카드 혜택 중 경쟁사가 비어 있는 곳이 어디야?", me=True)
        s += box(x + 20, y + 64, w - 40, 74, fill="#f3f7ff", stroke=BLUE)
        s += t(x + 34, y + 86, "오케스트레이터", 12, BLUE, 700)
        s += t(x + 34, y + 108, "입력 분석: 시판 카드 혜택 구조 질문", 12) + t(x + 34, y + 126, "→ 03 경쟁사 에이전트 호출", 12, BLUE, 600)
        s += box(x + 20, y + 152, w - 40, 134, fill=LIGHT)
        s += t(x + 34, y + 174, "03 경쟁사", 12, GRAY, 700)
        s += t(x + 34, y + 198, "놓친 혜택 환급 · 실적조건 완화: 0종 / 34종", 12, WARN, 600)
        s += t(x + 34, y + 222, "구독 할인형은 8종이 이미 채택", 12)
        s += t(x + 34, y + 246, "집계는 코드, 해석은 AI", 11, GRAY)
        return s
    return frame(9, "개별 에이전트 활용 · 담당 에이전트 호출", user_layout(c, history=("경쟁사 혜택 공백 질문", "GenZ 특화 신용카드")), "질문을 분석해 맞는 전문 에이전트를 오케스트레이터가 불러옵니다")


def b10():
    body = box(32, 56, 896, 400, fill="#fff")
    body += t(60, 88, "타 전문 영역이 필요하면 에이전트를 함께 호출해 협의", 15, NAVY, 700)
    body += box(60, 108, 840, 52, fill="#f3f7ff", stroke=BLUE)
    body += t(76, 130, "오케스트레이터", 12, BLUE, 700) + t(76, 150, "공백이 곧 수요는 아님 → 04 소비자(니즈), 02 트렌드(결제 습관)를 함께 호출", 12)
    body += agent_node(60, 190, 240, "03 경쟁사", "실적조건 완화 0종 / 34종")
    body += agent_node(360, 190, 240, "04 소비자", "디지털·절약 니즈")
    body += agent_node(660, 190, 240, "02 트렌드", "간편결제 일평균 1조464억원")
    body += arrow(300, 216, 360, 216, BLUE) + arrow(360, 226, 300, 226, BLUE) + arrow(600, 216, 660, 216, BLUE) + arrow(660, 226, 600, 226, BLUE)
    body += chip(110, 254, "혜택 공백", WARN, 90) + chip(410, 254, "니즈와 맞닿음", OK, 130) + chip(700, 254, "결제 접점이 앱으로", BLUE, 150)
    body += box(60, 296, 840, 90, fill=LIGHT)
    body += t(80, 322, "종합 의견 (의사결정 지원)", 12, GRAY, 700)
    body += t(80, 348, "공백 혜택과 디지털·절약 니즈는 부합하나, 간편결제 습관과", 14, NAVY, 600)
    body += t(80, 370, "혜택 불신이 발급 동기를 약화시킬 가능성", 14, NAVY, 600)
    body += box(60, 398, 840, 40, fill="#fff", stroke=OK) + t(80, 423, "최종 판단은 사람이 수행, 에이전트는 근거와 쟁점을 정리", 12, OK, 600)
    return frame(10, "개별 에이전트 활용 · 에이전트 협의", body, "필요하면 다른 전문가 에이전트를 함께 불러 의견을 모아 드립니다")



# ============ 사용자 화면 구성 샘플 ============

def sidebar(x, w, items, active=0):
    s = box(x, 56, w, 400, fill=LIGHT, stroke=LIGHT) + t(x + 12, 78, "대화 기록", 12, GRAY, 600)
    for i, h in enumerate(items):
        s += box(x + 8, 90 + i * 34, w - 16, 26, fill="#dfe7fb" if i == active else "#fff") + t(x + 16, 107 + i * 34, h, 11)
    s += box(x + 8, 420, w - 16, 26, fill="#fff", stroke=BLUE) + t(x + w / 2, 437, "+ 새 대화", 11, BLUE, 600, "middle")
    return s


def logrow(x, y, who, msg, color=GRAY, w=600):
    return f'<circle cx="{x}" cy="{y - 4}" r="3.5" fill="{color}"/>' + t(x + 12, y, who, 11, color, 700) + t(x + 112, y, msg, 11, NAVY)


def u1():
    """대화형: 왼쪽 채팅 기록, 가운데 대화 로그."""
    body = sidebar(32, 170, ["2030 투자 입문자 카드", "GenZ 특화 신용카드", "경쟁사 구조 질문", "어제 · 컨셉 이름 검토"])
    body += box(212, 56, 716, 400, fill="#fff")
    body += bubble(222, 70, 696, "2030 투자 입문자를 위한 새로운 신용카드를 기획해줘", me=True)
    body += box(222, 112, 696, 128, fill=LIGHT, stroke=LIGHT)
    body += t(238, 134, "오케스트레이터 · 진행 로그", 12, BLUE, 700)
    rows = [("intake", "타깃·카드 유형 해석 → 범위 확인 완료", OK), ("01 시장조사", "02 트렌드 · 03 경쟁사 · 04 소비자 동시 호출", BLUE),
            ("검증", "근거·출처·수치 대조 통과", OK), ("사람 확인", "기회 선택 대기 중", WARN)]
    for i, (who, m, c) in enumerate(rows):
        body += logrow(240, 160 + i * 22, who, m, c)
    body += box(222, 252, 696, 150, fill="#fff", stroke=BLUE)
    body += t(238, 274, "시장조사 요약", 12, GRAY, 700)
    body += t(238, 298, "투자 연계는 니즈 1순위이자 시판 카드의 빈칸이지만,", 13, NAVY, 600)
    body += t(238, 318, "증권사 연계 선례 존재, 차별화와 제휴 확보가 관건", 13, NAVY, 600)
    body += chip(238, 332, "근거 T1 신뢰도 0.6", BLUE, 140) + chip(388, 332, "투자 리워드 0종 / 34종", WARN, 170) + chip(568, 332, "충돌 1건 나란히", BAD, 120)
    body += box(238, 366, 130, 28, fill=BLUE, stroke=BLUE, r=6) + t(303, 385, "리포트로 보기", 12, "#fff", 600, "middle")
    body += box(222, 414, 696, 34, fill="#fff") + t(236, 436, "에이전트에게 질문하거나 다음 단계를 지시하세요", 12, GRAY) + box(858, 418, 52, 26, fill=BLUE, stroke=BLUE, r=6) + t(884, 436, "전송", 11, "#fff", 600, "middle")
    return frame(1, "사용자 뷰 · 대화형", body, "왼쪽에 대화 기록, 가운데에 대화와 진행 로그")


def u2():
    """연결도형: 대화 + 실시간 에이전트 네트워크."""
    body = sidebar(32, 116, ["2030 투자 입문자", "GenZ 특화", "경쟁사 질문"])
    body += box(156, 56, 300, 400, fill="#fff")
    body += bubble(164, 68, 284, "투자 입문자 카드 기획해줘", me=True)
    body += box(164, 108, 284, 150, fill=LIGHT, stroke=LIGHT)
    for i, (who, m, c) in enumerate([("01", "총괄 호출", BLUE), ("02·03·04", "동시 조사 중", BLUE), ("gate", "근거 검증 대기", GRAY)]):
        body += logrow(176, 134 + i * 24, who, m, c)
    body += t(176, 218, "02·03 완료, 04 소비자 진행 중", 11, GRAY)
    body += box(164, 270, 284, 90, fill="#fff", stroke=BLUE) + t(176, 292, "중간 요약", 11, GRAY, 700) + t(176, 314, "시판 카드 34종 중 투자 리워드 0종", 12, NAVY, 600) + t(176, 336, "트렌드 신호 5개 수집", 12, NAVY, 600)
    body += box(164, 414, 284, 34, fill="#fff") + t(176, 436, "질문 입력", 12, GRAY)
    body += box(468, 56, 460, 400, fill="#fff", stroke=BLUE)
    body += t(484, 80, "에이전트 연결 (실시간)", 13, NAVY, 700) + chip(780, 66, "● 실행 중", BLUE, 76) + chip(862, 66, "○ 완료", OK, 56)
    def node(cx, cy, w, label, state):
        col = {"run": BLUE, "done": OK, "wait": LINE, "opt": GRAY}[state]
        fill = "#eaf0ff" if state == "run" else "#f4fbf7" if state == "done" else "#fff"
        return box(cx - w / 2, cy - 17, w, 34, fill=fill, stroke=col, sw=2 if state == "run" else 1, dash="5 3" if state == "opt" else None) + t(cx, cy + 5, label, 11, NAVY, 600, "middle")
    O = (698, 296)
    ring = [((698, 190), 112, "01 시장조사 총괄", "run"), ((560, 240), 100, "06 컨셉", "wait"), ((836, 240), 112, "09 디자인·마케팅", "wait"),
            ((540, 296), 96, "07 시장성 검증", "wait"), ((856, 296), 96, "10 기획서", "wait"),
            ((560, 352), 100, "08 가드레일 (선택)", "opt"), ((836, 352), 100, "05 시장기회", "wait")]
    for (cx, cy), w, lb, st in ring:
        col = BLUE if st == "run" else LINE
        dash = 'stroke-dasharray="6 4"' if st == "opt" else ""
        body += f'<line x1="{O[0]}" y1="{O[1]}" x2="{cx}" y2="{cy}" stroke="{col}" stroke-width="{3 if st == "run" else 1.2}" {dash}/>'
    body += node(O[0], O[1], 130, "오케스트레이터", "done")
    for (cx, cy), w, lb, st in ring:
        body += node(cx, cy, w, lb, st)
    for i, (n, st) in enumerate([("02 트렌드", "done"), ("03 경쟁사", "done"), ("04 소비자", "run")]):
        cx = 610 + i * 88
        body += f'<line x1="698" y1="173" x2="{cx}" y2="142" stroke="{OK if st == "done" else BLUE}" stroke-width="1.5"/>'
        body += node(cx, 124, 82, n, st)
    body += t(698, 166, "동시 실행", 10, OK, 600, "middle")
    body += box(484, 398, 428, 50, fill=LIGHT, stroke=LIGHT)
    body += t(498, 417, "지금 연결", 11, GRAY, 700) + t(498, 438, "오케스트레이터 → 01 총괄 → 02 · 03 · 04 (병렬)", 12, NAVY, 600)
    return frame(2, "사용자 뷰 · 연결도형", body, "대화 옆에 지금 어떤 에이전트가 무엇과 연결되는지 실시간으로 표시")


def u3():
    """리포트형: 오른쪽 반이 결과 리포트(HTML)."""
    body = sidebar(32, 116, ["2030 투자 입문자", "GenZ 특화", "경쟁사 질문"])
    body += box(156, 56, 388, 400, fill="#fff")
    body += bubble(164, 68, 372, "최종 요약해서 신상품기획보고서로 만들어줘", me=True)
    body += box(164, 108, 372, 170, fill=LIGHT, stroke=LIGHT)
    body += t(176, 130, "최종 요약", 11, GRAY, 700) + t(176, 154, "함께쌓기 카드", 14, NAVY, 700)
    body += t(176, 178, "법무 확인 필요 항목 표시", 12) + t(176, 200, "미검증 항목 17건은 부록에 모음", 12) + t(176, 222, "채택 의향은 가정 기반 값", 12)
    body += box(176, 236, 130, 28, fill=BLUE, stroke=BLUE, r=6) + t(241, 255, "보고서로 보기", 12, "#fff", 600, "middle")
    body += box(164, 414, 372, 34, fill="#fff") + t(176, 436, "수정할 부분을 말해 보세요", 12, GRAY)
    body += report_mock(552, 56, "세칸", ("직전 3개월 합계 1위 영역에", "캐시백이 자동 배정되는 카드"), True, [("타깃", "만 19~29세 GenZ"), ("주요 혜택", "1위 영역 1.3%"), ("차별점", "영역 자동 배정")])
    return frame(3, "사용자 뷰 · 리포트형", body, "오른쪽 반이 결과 리포트(HTML)로 열립니다")



def r1():
    body = box(32, 56, 896, 400, fill="#fff")
    body += t(60, 88, "보고서 00 핵심 요약: 컨셉 · 주요 혜택 · 타깃 세그먼트 · 차별점", 15, NAVY, 700)
    body += f'<rect x="60" y="106" width="400" height="150" rx="10" fill="#14141a"/>' + t(78, 130, "컨셉", 11, "#d6ff3f", 700) + t(78, 172, "세칸", 36, "#d6ff3f", 800) + t(78, 200, "직전 3개월 이용액 합계가 가장 큰 영역에", 12, "#fff") + t(78, 218, "캐시백이 자동 배정되는 GenZ 특화 신용카드", 12, "#fff") + t(78, 240, "영역 선택 불필요 · 규칙에 따른 판정", 11, "#9fb3ff")
    def card(x, y, title, rows):
        c = box(x, y, 400, 150, fill="#fafbff", stroke=LINE) + t(x + 16, y + 24, title, 11, BLUE, 700)
        for i, (k, v) in enumerate(rows):
            c += f'<line x1="{x + 16}" y1="{y + 36 + i * 26}" x2="{x + 384}" y2="{y + 36 + i * 26}" stroke="{LINE}"/>' + t(x + 16, y + 54 + i * 26, k, 11, NAVY, 700) + t(x + 130, y + 54 + i * 26, v, 11)
        return c
    body += card(480, 106, "주요 혜택", [("1위 영역 캐시백", "1.3% (직전 3개월 합계 1위)"), ("나머지 2개 영역", "0.4%"), ("적용 조건", "전월 30만원 이상 · 월 한도 5천원"), ("연회비", "1만원")])
    body += card(60, 272, "타깃 세그먼트", [("연령", "만 19~29세"), ("결제 습관", "간편결제 등록 · 앱 발급"), ("핵심 니즈", "구독·디지털 1순위"), ("진입 장벽", "금융이력 부족 · 혜택 불신")])
    body += card(480, 272, "차별점", [("영역 선택 불필요", "자동 판정"), ("시판 카드 공백", "34종 중 0종 구조"), ("판정 규칙 공개", "앞·뒷면 · 앱 명시"), ("체리피킹 방어", "3개월 합계 · 월 한도")])
    return frame(9, "신상품기획보고서 · 핵심 요약", body, "컨셉·주요 혜택·타깃 세그먼트·차별점을 보고서 최상단에 배치")


def r2():
    body = box(32, 56, 896, 400, fill="#fff")
    body += t(60, 88, "보고서 02 포지셔닝 맵: 경쟁사 · 자사 카드 라인업 (가상 데이터)", 15, NAVY, 700)
    body += box(60, 104, 560, 336, fill="#fafbff", stroke=LINE)
    for gx in range(0, 6):
        x = 100 + gx * 100
        body += f'<line x1="{x}" y1="116" x2="{x}" y2="396" stroke="{LINE}"/>' + t(x, 414, str(gx * 2), 10, GRAY, 400, "middle")
    for gy, lab in enumerate(["50대", "40대", "30대", "20대"]):
        y = 140 + gy * 80
        body += f'<line x1="86" y1="{y}" x2="604" y2="{y}" stroke="{LINE}"/>' + t(80, y + 4, lab, 10, GRAY, 400, "end")
    body += t(350, 432, "혜택 구조 복잡도 (단순 → 복합)", 11, NAVY, 700, "middle")
    pts = [("트래블 프리미엄", 530, 150, "#0e8f80"), ("패밀리 케어", 400, 205, "#0e8f80"), ("라이프 플러스", 430, 232, "#0e8f80"), ("데일리 체크", 190, 345, "#0e8f80")]
    for n, x, y, col in pts:
        body += f'<circle cx="{x}" cy="{y}" r="8" fill="{col}"/>' + t(x + 13, y + 4, n, 11)
    for n, x, y in [("iD SELECT ALL", 460, 318), ("Discount Plan+", 360, 348), ("올바른 FLEX", 420, 378)]:
        body += f'<rect x="{x - 6}" y="{y - 6}" width="12" height="12" transform="rotate(45 {x} {y})" fill="#9a9a92"/>' + t(x + 13, y + 4, n, 11, GRAY)
    body += '<circle cx="250" cy="380" r="14" fill="#d6ff3f" stroke="#14141a" stroke-width="2.5"/>' + t(250, 384, "NEW", 9, "#14141a", 800, "middle") + t(272, 384, "세칸", 12, "#14141a", 800)
    body += t(650, 128, "범례", 11, GRAY, 700) + f'<circle cx="662" cy="148" r="7" fill="#d6ff3f" stroke="#14141a" stroke-width="2"/>' + t(676, 152, "신상품", 11) + '<circle cx="662" cy="172" r="7" fill="#0e8f80"/>' + t(676, 176, "자사 카드 라인업", 11) + f'<rect x="656" y="190" width="12" height="12" transform="rotate(45 662 196)" fill="#9a9a92"/>' + t(676, 200, "근접 경쟁 카드", 11)
    body += box(644, 224, 268, 100, fill=LIGHT, stroke=LIGHT) + t(658, 246, "자사 라인업 중복도 표", 11, BLUE, 700) + t(658, 268, "데일리 체크  낮음 · 교차 판매 가능", 11) + t(658, 288, "라이프 플러스  중간 · 구조 차별화", 11) + t(658, 308, "패밀리 케어  낮음", 11)
    body += t(644, 350, "※ 자사 카드 라인업·좌표는 가상 데이터", 11, WARN, 700) + t(644, 370, "고객사 카드 DB 연동 후 실제 값 반영", 11, GRAY)
    return frame(10, "신상품기획보고서 · 포지셔닝 맵", body, "경쟁사와 자사 카드 라인업 사이의 신상품 위치")

A = [a01, a02, s03, s04, a05, a06, s07, a08, a09, a10, s10]
B = [b01, b02, b03, b04, b05, b06, b07, b08, b09, b10]
for case, fns in (("A", A), ("B", B)):
    for i, fn in enumerate(fns, 1):
        NO[0] = i
        (OUT2 / f"{case}-{i:02d}.svg").write_text(fn(), encoding="utf-8")
for i, fn in enumerate([u1, u2, u3], 1):
    NO[0] = i
    (OUT2 / f"UI-{i}.svg").write_text(fn(), encoding="utf-8")
for nm, fn in (("R-1", r1), ("R-2", r2)):
    (OUT2 / f"{nm}.svg").write_text(fn(), encoding="utf-8")
print("ok", len(A), len(B))
