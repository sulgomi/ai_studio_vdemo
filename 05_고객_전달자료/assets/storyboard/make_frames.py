"""데모영상 스토리보드 장면 이미지(SVG 와이어프레임)를 만든다.

실행: python3 make_frames.py  (같은 폴더에 scene-01.svg ~ scene-10.svg 생성)
화면 구성은 ui/user-view.html, ui/dev-view.html 을 단순화한 것이다.
"""
from pathlib import Path
from xml.sax.saxutils import escape

W, H = 960, 540
OUT = Path(__file__).parent

NAVY = "#1f2a44"
BLUE = "#3b6ef5"
LIGHT = "#eef2fb"
LINE = "#c9d1e3"
GRAY = "#8a93a8"
OK = "#1f9d6b"
WARN = "#d9822b"
BAD = "#d64545"
FONT = "Pretendard, 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif"


def t(x, y, s, size=13, color=NAVY, weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
            f'fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{escape(s)}</text>')


def box(x, y, w, h, fill="#fff", stroke=LINE, r=8, sw=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')


def arrow(x1, y1, x2, y2, color=GRAY):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" '
            f'stroke-width="1.5" marker-end="url(#ah)"/>')


def chip(x, y, label, color=BLUE, w=None):
    w = w or 14 + len(label) * 12
    return box(x, y, w, 22, fill="#fff", stroke=color, r=11) + t(x + w / 2, y + 15, label, 11, color, 600, "middle")


def frame(no, title, body, caption):
    """브라우저 창 + 장면 번호 + 하단 자막 띠."""
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            '<defs><marker id="ah" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
            f'<path d="M0,0 L8,4 L0,8 z" fill="{GRAY}"/></marker></defs>'
            f'<rect width="{W}" height="{H}" fill="#f6f7fb"/>'
            + box(20, 16, W - 40, H - 80, fill="#fff", stroke=LINE, r=10)
            + f'<rect x="20" y="16" width="{W - 40}" height="28" rx="10" fill="{LIGHT}"/>'
            + "".join(f'<circle cx="{40 + i * 16}" cy="30" r="5" fill="{c}"/>' for i, c in enumerate(["#e46a6a", "#e8b84a", "#5cbf7a"]))
            + t(100, 35, title, 12, GRAY)
            + box(W - 112, 22, 84, 16, fill="#fff3e0", stroke=WARN, r=8) + t(W - 70, 34, "데모 모드", 10, WARN, 600, "middle"))
    tail = (f'<rect x="0" y="{H - 56}" width="{W}" height="56" fill="{NAVY}"/>'
            + t(24, H - 22, f"#{no:02d}", 16, "#9fb3ff", 700)
            + t(70, H - 22, caption, 15, "#fff", 500)
            + "</svg>")
    return head + body + tail


def user_layout(center, right=None, history=("2030 투자 입문자 카드",)):
    """사용자 뷰: 왼쪽 대화 기록, 가운데 채팅, 오른쪽 리포트(선택)."""
    s = box(32, 56, 170, 400, fill=LIGHT, stroke=LIGHT) + t(44, 78, "대화 기록", 12, GRAY, 600)
    for i, h in enumerate(history):
        s += box(42, 90 + i * 34, 150, 26, fill="#fff" if i else "#dfe7fb") + t(52, 107 + i * 34, h, 11)
    cw = 330 if right else 720
    s += box(212, 56, cw, 400, fill="#fff")
    s += center(212, 56, cw)
    if right:
        s += box(552, 56, 376, 400, fill="#fff", stroke=BLUE)
        s += right(552, 56)
    return s


def bubble(x, y, w, text, me=False, h=30):
    fill = BLUE if me else LIGHT
    color = "#fff" if me else NAVY
    bx = x + (w - min(w, 14 + len(text) * 12)) if me else x
    bw = min(w, 14 + len(text) * 12)
    return box(bx, y, bw, h, fill=fill, stroke=fill, r=12) + t(bx + 10, y + 19, text, 12, color)


def log_line(x, y, who, msg, color=GRAY):
    return t(x, y, f"▸ {who}", 11, color, 600) + t(x + 120, y, msg, 11, GRAY)


# ---------- 장면 ----------

def s01():
    body = (t(W / 2, 170, "카드 신상품 하나를 기획하려면", 22, GRAY, 400, "middle")
            + t(W / 2, 210, "시장조사 · 경쟁 분석 · 컨셉 · 검증 · 준법 · 디자인 · 기획서", 18, NAVY, 600, "middle"))
    xs = [130, 230, 330, 430, 530, 630, 730]
    for i, x in enumerate(xs):
        body += box(x, 250, 90, 60, fill=LIGHT) + t(x + 45, 285, ["조사", "경쟁", "컨셉", "검증", "준법", "디자인", "기획서"][i], 13, NAVY, 600, "middle")
        if i < 6:
            body += arrow(x + 90, 280, x + 100, 280)
    body += t(W / 2, 360, "AI 에이전트 팀이 이어서 수행하고, 사람은 다섯 곳에서 결정합니다", 16, BLUE, 600, "middle")
    body += t(W / 2, 400, "[현행 소요 기간: 고객 확인 후 기입]", 12, WARN, 400, "middle")
    return frame(1, "오프닝", body, "카드 상품기획 전 과정을 에이전트 팀이 나눠 맡습니다")


def s02():
    def c(x, y, w):
        s = bubble(x + 20, y + 20, w - 40, "2030 투자 입문자를 위한 새로운 신용카드를 기획해줘", me=True)
        s += log_line(x + 20, y + 80, "intake", "타깃·카드 유형·목표 해석")
        s += box(x + 20, y + 100, w - 40, 170, fill="#fff", stroke=BLUE)
        s += t(x + 36, y + 124, "H1 범위 확인", 13, BLUE, 700)
        rows = [("타깃", "2030 투자입문자"), ("카드 유형", "신용카드"), ("목표 채택 의향", "38% (가정치)"), ("가정", "고객 데이터 없이 공개 자료 사용")]
        for i, (k, v) in enumerate(rows):
            s += t(x + 36, y + 152 + i * 24, k, 12, GRAY) + t(x + 170, y + 152 + i * 24, v, 12)
        s += box(x + w - 200, y + 286, 80, 30, fill=BLUE, stroke=BLUE, r=6) + t(x + w - 160, y + 306, "확인", 12, "#fff", 600, "middle")
        s += box(x + w - 110, y + 286, 70, 30, r=6) + t(x + w - 75, y + 306, "수정", 12, NAVY, 600, "middle")
        return s
    return frame(2, "사용자 뷰 · E2E 상품기획", user_layout(c), "요청 한 줄을 넣으면 AI가 범위를 해석하고, 사람이 먼저 확인합니다")


def s03():
    body = box(32, 56, 896, 400, fill="#fff")
    body += box(390, 80, 180, 50, fill=NAVY, stroke=NAVY) + t(480, 110, "01 시장조사 총괄", 14, "#fff", 700, "middle")
    agents = [(110, "02 트렌드", "신호 5개 · 출처 5건"), (390, "03 경쟁사", "시판 34종 집계"), (670, "04 소비자", "니즈 순위 · 장벽")]
    for x, n, sub in agents:
        body += arrow(480, 130, x + 90, 200, BLUE)
        body += box(x, 200, 180, 56, fill=LIGHT, stroke=BLUE) + t(x + 90, 224, n, 13, NAVY, 700, "middle") + t(x + 90, 244, sub, 11, GRAY, 400, "middle")
        body += chip(x + 50, 262, "동시 실행", OK, 80)
    body += box(110, 310, 740, 120, fill="#fafbff")
    body += t(130, 336, "종합 결론", 12, GRAY, 600)
    body += t(130, 360, "투자 연계는 니즈 1순위이자 시판 카드의 빈칸이지만,", 14, NAVY, 600)
    body += t(130, 382, "증권사 연계 선례가 있어 차별화와 제휴 확보가 관건이다", 14, NAVY, 600)
    body += chip(130, 396, "T1 신뢰도 0.6", BLUE, 110) + chip(250, 396, "T2 0.55", BLUE, 80) + chip(340, 396, "투자 리워드 0종 / 34종", WARN, 170) + chip(520, 396, "충돌 1건 나란히 표시", BAD, 150)
    return frame(3, "사용자 뷰 · 시장조사 (멀티 에이전트)", body, "시장조사 총괄이 세 에이전트를 동시에 부르고, 근거와 출처를 붙여 종합합니다")


def s04():
    def c(x, y, w):
        s = t(x + 20, y + 30, "H2 기회 선택: 컨셉으로 넘길 기회를 골라 주세요", 13, BLUE, 700)
        cards = [("1순위", "2030 투자입문자 × 투자 연계", "점수 0.633 · 근거 T1, T2", True),
                 ("2순위", "사회초년생 × 투자 연계", "점수 0.622 · 근거 T2, T5", False),
                 ("3순위", "사회초년생 × 소셜(모임)", "근거 T3, 모임 합산 공백", False)]
        for i, (r, n, sub, sel) in enumerate(cards):
            yy = y + 50 + i * 100
            s += box(x + 20, yy, w - 40, 86, fill="#f3f7ff" if sel else "#fff", stroke=BLUE if sel else LINE, sw=2 if sel else 1)
            s += t(x + 36, yy + 26, r, 12, GRAY, 600) + t(x + 96, yy + 26, n, 14, NAVY, 700)
            s += t(x + 96, yy + 50, sub, 12, GRAY)
            s += t(x + 96, yy + 70, "위험: 제휴만 확보되면 경쟁사가 따라 하기 쉬움", 11, WARN)
            if sel:
                s += box(x + w - 110, yy + 28, 70, 30, fill=BLUE, stroke=BLUE, r=6) + t(x + w - 75, yy + 48, "선택", 12, "#fff", 600, "middle")
        return s
    return frame(4, "사용자 뷰 · E2E 상품기획", user_layout(c), "기회 점수는 코드가 계산하고, AI가 근거를 붙여 3개를 고르면 사람이 선택합니다")


def s05():
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
    body += t(60, 210, "07 시장성 검증 · 가상 고객 1,760명", 14, NAVY, 700)
    bars = [("기본", 0.396), ("경쟁사 모방", 0.281), ("혜택 20% 축소", 0.376), ("시장 위축", 0.333)]
    for i, (n, v) in enumerate(bars):
        yy = 230 + i * 34
        body += t(60, yy + 16, n, 12, GRAY) + box(170, yy + 2, 300, 20, fill=LIGHT, stroke=LIGHT, r=4)
        body += box(170, yy + 2, 300 * v / 0.5, 20, fill=BLUE if i == 0 else "#9fb3ff", stroke="none", r=4)
        body += t(170 + 300 * v / 0.5 + 8, yy + 17, f"{v * 100:.1f}%", 12, NAVY, 600)
    body += f'<line x1="{170 + 300 * 0.38 / 0.5}" y1="228" x2="{170 + 300 * 0.38 / 0.5}" y2="370" stroke="{BAD}" stroke-dasharray="4 3"/>' + t(170 + 300 * 0.38 / 0.5 + 4, 384, "목표 38%", 11, BAD)
    body += box(560, 210, 340, 160, fill="#fafbff")
    body += t(576, 234, "체리피커 반응", 12, WARN, 700)
    body += t(576, 258, "\"외식이랑 온라인만 이 카드로 긁고", 12) + t(576, 278, "나머지는 다른 카드로 돌릴게요.\"", 12)
    body += t(576, 310, "일반형 58% · 체리피커 21% · 휴면 위험형 15%", 11, GRAY)
    body += t(576, 352, "가상 고객 시뮬레이션(가정 기반) · 실제 전환율 아님", 11, BAD, 600)
    return frame(5, "사용자 뷰 · E2E 상품기획", body, "서로 다른 컨셉 3안을 코드가 평가하고, 가상 고객으로 시장성을 확인합니다")


def s06():
    body = box(32, 56, 896, 400, fill="#fff")
    body += t(60, 90, "08 가드레일 · 재무·준법 6개 항목 점검", 15, NAVY, 700)
    rows = [("G1", "이름·약속과 실제 작동 일치", "수정 필요", BAD), ("G2", "광고 표현(합산 혜택 오인)", "수정 필요", BAD),
            ("G3", "부가서비스 변경·지급 조건 고지", "사람 확인", WARN), ("G4", "그룹사 연계 개인정보", "판정", GRAY),
            ("G5", "투자권유·원금 손실 오인", "판정", GRAY), ("G6", "체리피킹 대비", "판정", GRAY)]
    for i, (g, n, st, col) in enumerate(rows):
        yy = 108 + i * 30
        body += t(60, yy + 16, g, 12, GRAY, 700) + t(96, yy + 16, n, 12) + chip(330, yy, st, col, 84)
    body += box(450, 100, 450, 190, fill="#fff5f5", stroke=BAD)
    body += t(470, 128, "G1 지적", 12, BAD, 700)
    body += t(470, 152, "'같이굴려요'(굴리다 = 자산을 불린다는 뉘앙스)가", 12)
    body += t(470, 172, "실제 구조보다 강하게 읽힘", 12)
    body += t(470, 204, "수정안", 12, OK, 700)
    body += t(470, 228, "한 줄 약속을 실제 작동대로 바꾸고,", 12) + t(470, 248, "'굴려서 불린다'는 수익 뉘앙스 카피 금지", 12)
    body += box(60, 310, 840, 110, fill=LIGHT)
    body += t(80, 336, "되돌림", 12, GRAY, 700)
    body += box(80, 352, 170, 44, fill="#fff", stroke=BAD) + t(165, 380, "같이굴려요 카드", 13, BAD, 700, "middle")
    body += arrow(250, 374, 330, 374, BLUE) + t(290, 366, "컨셉 재작업", 10, BLUE, 600, "middle")
    body += box(340, 352, 170, 44, fill="#fff", stroke=OK, sw=2) + t(425, 380, "함께쌓기 카드", 13, OK, 700, "middle")
    body += t(540, 372, "검증 결과가 컨셉과 이름을 실제로 바꿈", 13, NAVY, 600) + t(540, 394, "변경 이력은 기획서 부록에 남음", 12, GRAY)
    return frame(6, "사용자 뷰 · E2E 상품기획", body, "가드레일이 수정이 필요하다고 판정하면 컨셉으로 되돌아가 실제로 고칩니다")


def s07():
    body = box(32, 56, 896, 400, fill="#fff")
    body += t(60, 88, "09 디자인·마케팅 · 함께쌓기 카드", 15, NAVY, 700)
    names = [("A안 블록 탑", "#24345e"), ("B안 타이포", "#f2f2f2"), ("C안 친구들", "#3b6ef5")]
    for i, (n, col) in enumerate(names):
        x = 60 + i * 190
        body += f'<rect x="{x}" y="110" width="170" height="106" rx="10" fill="{col}" stroke="{LINE}"/>'
        body += t(x + 14, 200, "함께쌓기", 13, "#fff" if i != 1 else NAVY, 700)
        body += t(x + 85, 236, n, 12, NAVY, 600, "middle")
    body += f'<rect x="72" y="150" width="20" height="12" fill="#9fb3ff"/><rect x="72" y="138" width="20" height="12" fill="#c9d6ff"/><rect x="72" y="126" width="20" height="12" fill="#e6ecff"/>'
    body += box(640, 100, 260, 300, fill="#111", stroke="#111")
    body += t(770, 130, "영상 스토리보드 미리보기", 11, "#ccc", 400, "middle")
    body += box(700, 145, 140, 200, fill="#2a2f45", stroke="#444") + t(770, 250, "릴스 9:16", 12, "#fff", 600, "middle")
    body += f'<polygon points="760,280 760,304 782,292" fill="#fff"/>'
    body += t(770, 370, "릴스 · 유튜브 · 홍보 3종", 11, "#ccc", 400, "middle")
    body += t(60, 270, "이름 후보", 12, GRAY, 700)
    body += chip(60, 282, "함께쌓기 카드 · 추천", OK, 150) + chip(220, 282, "모아나눔 카드", GRAY, 110) + chip(340, 282, "챌린지메이트 카드", GRAY, 140)
    body += t(60, 336, "자동 검수: 색 대비 4.5:1 · 금칙어 · 혜택 숫자 변경 · 원금 손실 고지", 12, GRAY)
    body += box(60, 356, 300, 40, fill="#fff", stroke=BLUE) + t(76, 381, "H5 영상 렌더 확정", 13, BLUE, 700) + box(270, 361, 80, 30, fill=BLUE, stroke=BLUE, r=6) + t(310, 381, "이대로 확정", 11, "#fff", 600, "middle")
    return frame(7, "사용자 뷰 · E2E 상품기획", body, "이름, 카드 시안 3개, 영상 스토리보드까지 만들고 사람이 확정해야 렌더합니다")


def s08():
    def c(x, y, w):
        s = bubble(x + 20, y + 20, w - 40, "최종 요약해서 리포트화해줘", me=True)
        s += box(x + 20, y + 70, w - 40, 150, fill=LIGHT)
        s += t(x + 34, y + 94, "최종 요약", 12, GRAY, 700)
        s += t(x + 34, y + 118, "함께쌓기 카드", 14, NAVY, 700)
        s += t(x + 34, y + 142, "채택 의향 39.6% (가정 기반)", 12)
        s += t(x + 34, y + 164, "법무 확인 필요 항목 표시", 12)
        s += t(x + 34, y + 186, "미검증 항목 17건 부록", 12)
        s += box(x + 20, y + 240, 140, 32, fill=BLUE, stroke=BLUE, r=6) + t(x + 90, y + 261, "리포트로 보기", 12, "#fff", 600, "middle")
        return s

    def r(x, y):
        s = t(x + 16, y + 28, "2030 투자입문자 대상 신규 신용카드 기획안", 13, NAVY, 700)
        s += t(x + 16, y + 48, "\"내 적립 포인트 일부를, 모임과 함께 쌓아요.\"", 11, GRAY)
        secs = ["1. 요약", "2. 시장 조사와 기획 배경", "3. 신상품 컨셉과 가치 제안", "4. 재무 타당성과 사업 효과", "5. 마케팅 전략 방향", "6. 홍보 영상 콘셉트 보드", "7. 추진 일정과 부서별 R&R", "부록"]
        for i, n in enumerate(secs):
            s += t(x + 24, y + 80 + i * 24, n, 12, BLUE if i == 1 else NAVY, 600 if i == 1 else 400)
        s += box(x + 180, y + 96, 180, 92, fill="#fff", stroke=BLUE)
        s += t(x + 190, y + 116, "근거 T1", 11, BLUE, 700)
        s += t(x + 190, y + 136, "출처: 언론 보도", 11, GRAY)
        s += t(x + 190, y + 154, "발행일 · 신뢰도 0.6", 11, GRAY)
        s += t(x + 190, y + 174, "18개월 이내 ✓", 11, OK)
        s += box(x + 16, y + 360, 100, 28, r=6) + t(x + 66, y + 379, "HTML 저장", 11, NAVY, 600, "middle")
        s += box(x + 126, y + 360, 70, 28, r=6) + t(x + 161, y + 379, "인쇄", 11, NAVY, 600, "middle")
        return s
    return frame(8, "사용자 뷰 · 결과 문서화", user_layout(c, r), "결과는 7개 섹션 기획서로 정리되고, 문장마다 근거 출처를 따라갈 수 있습니다")


def s09():
    body = box(32, 56, 440, 400, fill="#fff")
    body += t(48, 82, "개별 에이전트 모드 · 단일 에이전트", 13, NAVY, 700)
    body += chip(48, 94, "03 경쟁사", BLUE, 90) + chip(146, 94, "02 트렌드", GRAY, 90) + chip(244, 94, "04 소비자", GRAY, 90)
    body += bubble(48, 132, 408, "시판 카드 중 어디가 붐비고 어디가 비어 있어?", me=True)
    body += box(48, 176, 408, 120, fill=LIGHT)
    body += t(62, 200, "붐비는 혜택: 청구할인형 15 · 해외결제 14 · 외식·카페 12", 12)
    body += t(62, 224, "빈 혜택: 투자 리워드 0 · 포인트 주식 전환 0", 12, WARN, 600)
    body += t(62, 248, "가까운 카드: ZERO Edition3 · 현대카드 M · LOCA LIKIT 1.2", 12)
    body += t(62, 280, "이 질문은 시장조사 모드로 이어갈까요?", 11, BLUE)
    body += box(488, 56, 440, 400, fill="#fff")
    body += t(504, 82, "개발 뷰 · 실행 기록", 13, NAVY, 700)
    ev = [("call", "research_lead", GRAY), ("call", "trend ∥ competitor ∥ consumer", BLUE), ("gate", "실현가능성 통과", OK),
          ("human_wait", "H2 기회 선택", WARN), ("validate", "concept 3안 검사", GRAY), ("reject", "guardrail G1·G2 fix", BAD),
          ("rework", "concept 재작업 1/3", BLUE), ("validate", "plan_doc 수치 대조 통과", OK), ("run_end", "약 9.8분 (리허설)", GRAY)]
    for i, (k, m, col) in enumerate(ev):
        yy = 104 + i * 34
        body += box(504, yy, 408, 28, fill="#fff", stroke=LINE, r=6) + t(516, yy + 19, k, 11, col, 700) + t(616, yy + 19, m, 11, NAVY)
    return frame(9, "단일 에이전트 대화 · 개발 뷰", body, "에이전트 하나와 직접 대화할 수도 있고, 모든 호출과 되돌림은 기록으로 남습니다")


def s10():
    body = t(W / 2, 110, "데모에서 보신 것", 20, NAVY, 700, "middle")
    cols = [("실제 AI가 만든 것", ["시장조사 결과와 출처", "컨셉 3안", "가드레일 판정과 수정안", "이름 · 시안 · 스토리보드", "기획서 문장"], BLUE),
            ("코드가 계산한 것", ["기회 점수", "손익 · 유사도 · 복잡도", "가상 고객 시뮬레이션", "통과 기준 · 되돌림", "수치 대조 검사"], OK),
            ("가정 · 확인 필요", ["세그먼트 수치(가정치)", "통과 기준값(가정치)", "법무 확인 필요 항목", "데모는 저장된 실행 재사용", "실제 전환율 아님"], WARN)]
    for i, (h, items, col) in enumerate(cols):
        x = 80 + i * 280
        body += box(x, 140, 250, 230, fill="#fff", stroke=col, sw=2)
        body += t(x + 125, 170, h, 14, col, 700, "middle")
        for j, it in enumerate(items):
            body += t(x + 24, 204 + j * 32, "· " + it, 12)
    body += t(W / 2, 410, "다음 단계: 설계서 피드백 → 2차 데모(실구동, 즉석 입력)", 15, NAVY, 600, "middle")
    return frame(10, "클로징", body, "무엇이 AI이고 무엇이 계산이며 무엇이 가정인지 한 장으로 공개합니다")


for i, fn in enumerate([s01, s02, s03, s04, s05, s06, s07, s08, s09, s10], 1):
    (OUT / f"scene-{i:02d}.svg").write_text(fn(), encoding="utf-8")
print("ok")
