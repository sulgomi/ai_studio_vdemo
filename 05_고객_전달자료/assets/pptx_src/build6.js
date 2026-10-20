const pptxgen = require("pptxgenjs");
const fs = require("fs");
const MODE = process.argv[2] || "wire"; // wire | real
const OUT = process.argv[3] || ("demo_storyboard_"+MODE+".pptx");
const { applyTheme } = require("/Users/sul/.claude/skills/synced/eae6a236-fccb-4d9f-832f-0367f63bfeb4_9584d1dc-acc1-4e17-94cf-13e524375149/pptx/scripts/apply_theme.js");
const { A, B } = require("./data4.js");

const THEME = { name:"CardAgentStoryboard", headFontFace:"Malgun Gothic", bodyFontFace:"Malgun Gothic",
 colors:{dk1:"111827",lt1:"FFFFFF",dk2:"243049",lt2:"F1F4F8",accent1:"0E8F80",accent2:"E4572E",accent3:"E9A92B",accent4:"4C63D2",accent5:"5B6577",accent6:"2EC4A6",hlink:"0E8F80",folHlink:"5B6577"}};

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.title = "카드 신상품 기획 AI 에이전트 — 데모 영상 스토리보드";
pres.author = "PM";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

// ---------- layouts ----------
const titlePh = (x,y,w,h,size,color) => ({ placeholder:{ options:{ name:"title", type:"title", x,y,w,h, fontSize:size, bold:true, color, margin:0, valign:"middle", align:"left" }, text:"" }});
pres.defineSlideMaster({ title:"COVER_DARK", masterName:"COVER_DARK", background:{ color:C.text1 },
  objects:[ titlePh(0.8,2.0,11.5,1.6,44,C.background1) ] });
pres.defineSlideMaster({ title:"SECTION_DARK", masterName:"SECTION_DARK", background:{ color:C.text1 },
  objects:[ titlePh(0.8,0.6,11.5,1.4,40,C.background1),
   { text:{ text:"카드 신상품 기획 AI 에이전트 · 데모 영상 스토리라인", options:{ x:0.8, y:7.0, w:8, h:0.3, fontSize:10, color:C.background2, margin:0, isTextBox:true } } },
   { text:{ text:"", options:{ x:0,y:0,w:0.01,h:0.01 } } } ].slice(0,2) });
pres.defineSlideMaster({ title:"CONTENT", masterName:"CONTENT", background:{ color:C.background1 },
  objects:[ titlePh(0.5,0.35,12.3,0.85,32,C.text1),
   { text:{ text:"카드 신상품 기획 AI 에이전트 · 데모 스토리라인 (초안)", options:{ x:0.5, y:7.05, w:9, h:0.3, fontSize:10, color:C.accent5, margin:0, isTextBox:true } } } ],
  slideNumber:{ x:12.2, y:7.05, w:0.6, h:0.3, fontSize:10, color:C.accent5, align:"right" } });
pres.defineSlideMaster({ title:"SCENE", masterName:"SCENE", background:{ color:C.background1 },
  objects:[ titlePh(1.65,0.35,8.6,0.9,28,C.text1),
   { text:{ text:"카드 신상품 기획 AI 에이전트 · 데모 스토리라인 (초안)", options:{ x:0.5, y:7.05, w:9, h:0.3, fontSize:10, color:C.accent5, margin:0, isTextBox:true } } } ],
  slideNumber:{ x:12.2, y:7.05, w:0.6, h:0.3, fontSize:10, color:C.accent5, align:"right" } });

const T = (s, text, o) => s.addText(text, Object.assign({ isTextBox:true, margin:0, valign:"top", color:C.text1, fontSize:14 }, o));
const label = (s, text, x, y, color) => T(s, text, { x, y, w:3, h:0.28, fontSize:12, bold:true, color, charSpacing:2 });


const shotPath = (c,n)=>`${__dirname}/img/shot-${c}-${n}.png`;
const hasShot = (c,n)=>MODE==="real"&&fs.existsSync(shotPath(c,n));
const SCENE_IMG = (c,n)=>hasShot(c,n)?shotPath(c,n):`${__dirname}/img/${c}-${n}c.png`;
const IW=7.9, IH=3.97, RX=8.7, RW=4.13;

function sceneSlide(sc, accent, tag, section, total, caseL) {
  const useImg = true;
  const isShot = hasShot(caseL, sc.no);
  const s = pres.addSlide({ masterName:"SCENE", sectionTitle:section });
  s.addShape(pres.ShapeType.ellipse, { x:0.5, y:0.35, w:0.95, h:0.95, fill:{ color:accent }, line:{ color:accent }, objectName:"장면번호원" });
  T(s, sc.no, { x:0.5, y:0.35, w:0.95, h:0.95, align:"center", valign:"middle", fontSize:24, bold:true, color:C.background1, objectName:"장면번호" });
  s.addText(sc.title, { placeholder:"title" });
  s.addShape(pres.ShapeType.roundRect, { x:10.3, y:0.55, w:2.53, h:0.5, rectRadius:0.08, fill:{ color:C.background2 }, line:{ color:C.background2 }, objectName:"장면위치" });
  T(s, `${tag} · 장면 ${+sc.no} / ${total}`, { x:10.3, y:0.55, w:2.53, h:0.5, align:"center", valign:"middle", fontSize:12, bold:true, color:C.text2 });

  // image slot (16:9). 실제 캡처로 교체: 이미지 우클릭 > 그림 바꾸기
  if (useImg) {
    s.addImage({ path:SCENE_IMG(caseL, sc.no), x:0.5, y:1.55, w:IW, h:IH, altText:`장면 ${sc.no} 화면`, objectName:"화면이미지(교체)" });
    s.addShape(pres.ShapeType.rect, { x:0.5, y:1.55, w:IW, h:IH, fill:{ color:C.background1, transparency:100 }, line:{ color:"C9D1E3", width:1 } });
  } else {
    s.addShape(pres.ShapeType.rect, { x:0.5, y:1.55, w:IW, h:IH, fill:{ color:C.background2 }, line:{ color:C.accent5, width:1.5, dashType:"dash" }, objectName:"화면이미지(교체)" });
    T(s, ["화면 캡처 이미지 영역", { text:"와이어프레임 · 이 도형을 지우고 캡처 이미지를 넣어 주세요", options:{ fontSize:14, bold:false, color:C.accent5, breakLine:false } }].map((t,i)=> typeof t==="string" ? { text:t, options:{ fontSize:22, bold:true, color:C.text2, breakLine:true } } : t), { x:0.8, y:2.85, w:7.0, h:1.1, align:"center" });
  }
  s.addShape(pres.ShapeType.roundRect, { x:0.65, y:1.7, w:(isShot?1.75:1.45), h:0.34, rectRadius:0.05, fill:{ color:(isShot?C.accent6:C.accent3) }, line:{ color:(isShot?C.accent6:C.accent3) }, objectName:(isShot?"캡처태그":"와이어프레임태그") });
  T(s, isShot?"실제 화면 캡처":"와이어프레임", { x:0.65, y:1.7, w:(isShot?1.75:1.45), h:0.34, align:"center", valign:"middle", fontSize:12, bold:true, color:C.text1 });

  // subtitle bar
  s.addShape(pres.ShapeType.rect, { x:0.5, y:5.64, w:IW, h:0.75, fill:{ color:C.text1 }, line:{ color:C.text1 }, objectName:"자막막대" });
  T(s, [{ text:"자막  ", options:{ bold:true, color:C.accent3, fontSize:12 } },{ text:sc.cap, options:{ color:C.background1, fontSize:14 } }], { x:0.75, y:5.64, w:IW-0.5, h:0.75, valign:"middle", objectName:"자막" });

  // right column
  label(s, "화면 구성", RX, 1.55, accent);
  const runs = sc.screen.map((t,i)=>({ text:t, options:{ bullet:{ indent:16 }, breakLine:i<sc.screen.length-1, paraSpaceAfter:6 } }));
  T(s, runs, { x:RX, y:1.9, w:RW, h:2.4, fontSize:14, objectName:"장면설명" });
  label(s, "핵심 내용", RX, 4.4, accent);
  s.addShape(pres.ShapeType.roundRect, { x:RX, y:4.72, w:RW, h:1.98, rectRadius:0.06, fill:{ color:C.background2 }, line:{ color:C.background2 }, objectName:"핵심내용틀" });
  T(s, sc.narr, { x:RX+0.18, y:4.82, w:RW-0.36, h:1.8, fontSize:14, objectName:"핵심내용" });
  s.addNotes(`${tag} 장면 ${sc.no}: ${sc.title}\n자막: ${sc.cap}\n핵심 내용: ${sc.narr}`);
}


function flowSlide(title, sub, scenes, accent, section) {
  const s = pres.addSlide({ masterName:"SECTION_DARK", sectionTitle:section });
  s.addText(title, { placeholder:"title" });
  T(s, sub, { x:0.8, y:2.15, w:11.7, h:0.8, fontSize:16, color:C.background2 });
  const n = scenes.length, per = Math.ceil(n/2), gap = 0.15, x0 = 0.8, cw = (11.73 - gap*(per-1))/per;
  scenes.forEach((sc,i)=>{
    const r = Math.floor(i/per), c = i%per, x = x0 + c*(cw+gap), y = 3.15 + r*1.7, key = sc.key;
    s.addShape(pres.ShapeType.roundRect, { x, y, w:cw, h:1.5, rectRadius:0.06, fill:{ color: key ? accent : C.text2 }, line:{ color: key ? accent : C.text2 }, objectName:`흐름칩${sc.no}` });
    T(s, "#"+sc.no, { x:x+0.15, y:y+0.12, w:1, h:0.3, fontSize:12, bold:true, color: key ? C.background1 : C.accent6 });
    T(s, sc.short, { x:x+0.12, y:y+0.5, w:cw-0.2, h:0.9, fontSize:14, bold:true, color:C.background1 });
  });
  T(s, "채움 표시 장면: 핵심 장면", { x:0.8, y:6.7, w:11.7, h:0.3, fontSize:12, color:C.background2 });
}
const tbl = (rows, opts) => rows;
const hd = (t,c)=>({ text:t, options:{ bold:true, color:C.background1, fill:{ color:c }, fontSize:14, valign:"middle" } });
const cell = (t,b)=>({ text:t, options:{ fontSize:13, valign:"middle", bold:!!b, color:C.text1 } });

// ---------- 1. cover ----------
pres.addSection({ title:"개요" });
let s = pres.addSlide({ masterName:"COVER_DARK", sectionTitle:"개요" });
s.addText("카드 신상품 기획 AI 에이전트\n데모 영상 스토리라인 제안", { placeholder:"title" });
T(s, "요청 한 줄에서 기획서까지, 에이전트 팀의 협업 과정을 보여 주는 3분대 영상. 2개 시나리오 안 중 1개를 선택해 제작", { x:0.8, y:3.9, w:9.5, h:1.2, fontSize:18, color:C.background2 });
T(s, (MODE==="real" ? "실제 화면 버전" : "와이어프레임 버전") + "  ·  초안  ·  2026-10-20", { x:0.8, y:6.6, w:9, h:0.3, fontSize:12, color:C.background2 });

// ---------- 2. key messages ----------
s = pres.addSlide({ masterName:"CONTENT", sectionTitle:"개요" });
s.addText("영상 핵심 메시지 5가지", { placeholder:"title" });
const big = [
 ["01","다수 에이전트의 동시 수행","트렌드·경쟁사·소비자 에이전트가 동시에 조사하고, 근거별 출처·신뢰도를 부여해 종합"],
 ["02","에이전트 간 상호 협의","컨셉·검증·디자인 에이전트가 결과와 쟁점을 교환하며 결론을 보완. 가드레일은 필요 시 추가되는 선택 기능"],
 ["03","근거 기반 통합 보고서","6개 에이전트 결과를 주제별로 통합한 신상품기획보고서 제공, 문장별 근거 출처 확인 가능"],
];
big.forEach((b,i)=>{
  const x = 0.5 + i*4.17;
  s.addShape(pres.ShapeType.roundRect, { x, y:1.5, w:3.98, h:3.1, rectRadius:0.08, fill:{ color:C.text1 }, line:{ color:C.text1 }, shadow:{ type:"outer", color:"111827", opacity:0.2, blur:8, offset:3, angle:90 }, objectName:`핵심카드${b[0]}` });
  T(s, b[0], { x:x+0.3, y:1.7, w:1, h:0.6, fontSize:32, bold:true, color:C.accent6 });
  T(s, b[1], { x:x+0.3, y:2.4, w:3.4, h:0.7, fontSize:20, bold:true, color:C.background1 });
  T(s, b[2], { x:x+0.3, y:3.2, w:3.4, h:1.3, fontSize:14, color:C.background2 });
});
const small = [
 ["04","필요 전문가의 자동 호출","질문 입력만으로 오케스트레이터가 담당 에이전트를 호출, 타 영역이 필요하면 함께 호출해 협의"],
 ["05","사람의 결정과 가정의 구분 공개","범위·기회·컨셉 단계는 사람이 확인, 시뮬레이션 수치는 가정 기반임을 화면에 표기"],
];
small.forEach((b,i)=>{
  const x = 0.5 + i*6.2;
  s.addShape(pres.ShapeType.roundRect, { x, y:4.9, w:6.1, h:1.85, rectRadius:0.08, fill:{ color:C.background2 }, line:{ color:C.background2 }, objectName:`보조카드${b[0]}` });
  T(s, b[0], { x:x+0.3, y:5.1, w:0.8, h:0.5, fontSize:24, bold:true, color:C.accent1 });
  T(s, b[1], { x:x+1.1, y:5.12, w:4.8, h:0.4, fontSize:16, bold:true });
  T(s, b[2], { x:x+1.1, y:5.65, w:4.8, h:1.0, fontSize:14, color:C.text2 });
});

// ---------- 3. flow overview ----------
s = pres.addSlide({ masterName:"CONTENT", sectionTitle:"개요" });
s.addText("영상 진행 순서", { placeholder:"title" });
const steps = [["요청","입력·범위 확인"],["시장조사","동시 조사"],["기회 선택","3개 중 선택"],["컨셉·검증","평가·시장성"],["협의·보완","에이전트 간 협의"],["디자인·마케팅","시안·스토리보드"],["기획서","통합 보고서"]];
const sw = 1.6, sg = 0.18;
steps.forEach((st,i)=>{
  const x = 0.5 + i*(sw+sg), hi = (i===1||i===4||i===6);
  s.addShape(pres.ShapeType.roundRect, { x, y:1.8, w:sw, h:2.2, rectRadius:0.08, fill:{ color: hi ? C.accent1 : C.background2 }, line:{ color: hi ? C.accent1 : C.background2 }, objectName:`단계${i+1}` });
  T(s, String(i+1), { x:x+0.15, y:1.95, w:0.6, h:0.5, fontSize:24, bold:true, color: hi ? C.background1 : C.accent1 });
  T(s, st[0], { x:x+0.15, y:2.6, w:sw-0.25, h:0.5, fontSize:16, bold:true, color: hi ? C.background1 : C.text1 });
  T(s, st[1], { x:x+0.15, y:3.1, w:sw-0.25, h:0.8, fontSize:14, color: hi ? C.background1 : C.text2 });
});
[["길이","본편 3분대"],["진행 방식","저장된 실행 기록을 재생하는 데모 모드, 화면에 상시 표기"],["자막","한국어 자막 상시 표시, 나레이션 없음"]].forEach((f,i)=>{
  const x = 0.5 + i*4.17;
  T(s, f[0], { x, y:4.5, w:3.9, h:0.3, fontSize:12, bold:true, color:C.accent1 });
  T(s, f[1], { x, y:4.85, w:3.9, h:1.0, fontSize:16 });
});
T(s, "채움 표시 단계: 비중이 큰 장면. 영상 후반에 개별 활용 장면(질문 입력 → 담당 에이전트 호출 → 필요 시 타 전문가와 협의) 구성", { x:0.5, y:6.2, w:12.3, h:0.6, fontSize:12, color:C.accent5 });

// ---------- 3b. report structure (가안) ----------
s = pres.addSlide({ masterName:"CONTENT", sectionTitle:"개요" });
s.addText("신상품기획보고서 구성(가안)", { placeholder:"title" });
const agents = [["시장조사","트렌드 · 경쟁사 · 소비자"],["시장기회","기회 셀 선정"],["컨셉","컨셉 3안 · 코드 평가"],["시장성 검증","가상 고객 시뮬레이션"],["가드레일 (선택)","재무·준법 점검"],["디자인·마케팅","이름 · 시안 · 스토리보드"]];
T(s, "입력: 6개 에이전트", { x:0.5, y:1.4, w:3.2, h:0.3, fontSize:12, bold:true, color:C.accent1 });
agents.forEach((a,i)=>{
  const y = 1.75 + i*0.76;
  s.addShape(pres.ShapeType.roundRect, { x:0.5, y, w:3.3, h:0.64, rectRadius:0.06, fill:{ color: i===4 ? C.background1 : C.background2 }, line:{ color: i===4 ? C.accent5 : C.background2, dashType: i===4 ? "dash" : "solid", width:1 }, objectName:`입력에이전트${i+1}` });
  T(s, a[0], { x:0.65, y:y+0.06, w:3.0, h:0.28, fontSize:14, bold:true });
  T(s, a[1], { x:0.65, y:y+0.34, w:3.0, h:0.24, fontSize:12, color:C.accent5 });
});
s.addShape(pres.ShapeType.rightArrow, { x:3.95, y:3.5, w:0.5, h:0.5, fill:{ color:C.accent1 }, line:{ color:C.accent1 }, objectName:"통합화살표" });
T(s, "통합", { x:3.9, y:4.05, w:0.6, h:0.3, fontSize:12, bold:true, color:C.accent1, align:"center" });
// report mock cover
s.addShape(pres.ShapeType.roundRect, { x:4.6, y:1.4, w:8.23, h:1.55, rectRadius:0.06, fill:{ color:C.text1 }, line:{ color:C.text1 }, objectName:"보고서표지" });
T(s, "NEW PRODUCT PLANNING REPORT", { x:4.85, y:1.55, w:4.5, h:0.25, fontSize:10, bold:true, color:C.accent6 });
T(s, "신상품기획보고서", { x:4.85, y:1.85, w:4.5, h:0.6, fontSize:28, bold:true, color:C.background1 });
T(s, "제목·대표 이미지(카드 시안)·핵심 4요소를 최상단에 배치", { x:4.85, y:2.5, w:4.6, h:0.3, fontSize:12, color:C.background2 });
[[10.0,1.7,0.8,1.05,"E9A92B"],[10.95,1.55,0.9,1.2,"2EC4A6"],[11.95,1.7,0.8,1.05,"4C63D2"]].forEach((c,i)=>{
  s.addShape(pres.ShapeType.roundRect, { x:c[0], y:c[1], w:c[2], h:c[3], rectRadius:0.08, fill:{ color:c[4] }, line:{ color:C.background1, width:1 }, objectName:`대표이미지${i+1}` });
});
const rrows = [
 [hd("섹션",C.text2),hd("입력 에이전트",C.text2),hd("주요 내용",C.text2)],
 [cell("00 핵심 요약",1),cell("전체"),cell("컨셉·주요 혜택·타깃 세그먼트·차별점 중심 요약")],
 [cell("01 시장과 기회",1),cell("시장조사, 시장기회"),cell("트렌드·경쟁 구도·소비자 니즈, 기회 선택 근거")],
 [cell("02 상품 컨셉·포지셔닝",1),cell("컨셉"),cell("혜택 구조, 후보 비교, 포지셔닝 맵(경쟁사·자사 라인업)")],
 [cell("03 시장성",1),cell("시장성 검증"),cell("채택 의향·손익·시나리오(가정 기반)")],
 [cell("04 브랜드·디자인·마케팅",1),cell("디자인·마케팅"),cell("이름, 카드 시안 3안, 마케팅 방향")],
 [cell("05 리스크·확인 사항",1),cell("가드레일(선택), 전체"),cell("점검 결과, 미검증 항목, 추가 조사 주제")],
 [cell("06 의사결정 요청",1),cell("전체"),cell("컨셉 확정, 법무 확인 배정, 영상 제작 여부")],
 [cell("부록",1),cell("전체"),cell("에이전트별 원자료, 근거 출처")],
];
s.addTable(rrows, { x:4.6, y:3.1, w:8.23, colW:[2.4,2.1,3.73], rowH:0.36, border:{ type:"solid", pt:0.75, color:"D7DCE5" }, fill:{ color:C.background1 }, margin:[0.03,0.1,0.03,0.1], fontSize:12, objectName:"보고서구성표" });
T(s, "에이전트별 결과의 순차 나열이 아닌 주제별 통합 구성, 원자료는 부록에 수록", { x:0.5, y:6.62, w:12.3, h:0.3, fontSize:12, color:C.accent5 });

// ---------- 4. pick one ----------
s = pres.addSlide({ masterName:"CONTENT", sectionTitle:"개요" });
s.addText("시나리오 안 비교 (택일)", { placeholder:"title" });
const rows = [
 [hd("",C.text1),hd("안 A: 2030 투자입문자 신용카드",C.accent1),hd("안 B: GenZ 특화 신용카드",C.accent2)],
 [cell("입력 요청",1),cell("“2030 투자 입문자를 위한 새로운 신용카드를 기획해줘”"),cell("“GenZ 특화 신용카드 만들어줘”")],
 [cell("카드 성격",1),cell("투자 연계 카드"),cell("일반 소비 카드 (투자 연계 제외)")],
 [cell("강조 장면",1),cell("협의를 통한 카드 이름 변경, 경쟁사 모방 시 시장성 변화 비교, 개별 활용 시 타 전문가 협의"),cell("쟁점 교환을 통한 컨셉 재설계, 근거 부족 시 타 에이전트 재조사 요청, 카드 시안 이미지, 개별 활용 시 타 전문가 협의")],
 [cell("화면 근거",1),cell("저장된 실행 기록 재생"),cell("2026-10-20 실제 실행 기록 재생")],
 [cell("유의 사항",1),cell("투자 연계 표현은 법무 확인 필요, 투자 권유로 읽히지 않도록 표기"),cell("투자 규제와 무관해 외부 공유 부담이 낮은 편, 장면 구성은 초안")],
];
s.addTable(rows, { x:0.5, y:1.45, w:12.33, colW:[2.2,5.0,5.13], rowH:[0.55,0.7,0.6,1.2,0.6,1.2], border:{ type:"solid", pt:0.75, color:"D7DCE5" }, fill:{ color:C.background1 }, margin:[0.05,0.12,0.05,0.12], objectName:"안비교표" });
T(s, "두 안 모두 동일한 에이전트 팀이 동일한 순서로 수행하는 모습을 제시, 영상에는 1개 안만 사용", { x:0.5, y:6.55, w:12.3, h:0.3, fontSize:12, color:C.accent5 });

// ---------- 5. disclosures ----------
s = pres.addSlide({ masterName:"CONTENT", sectionTitle:"개요" });
s.addText("영상 내 명시 사항", { placeholder:"title" });
[["데모 모드","저장된 실행을 재생한 화면에 ‘데모 모드’ 표기 상시 유지"],
 ["가정 기반 수치","채택 의향 등 수치에 ‘가상 고객 시뮬레이션(가정 기반) · 실제 전환율 아님’ 병기"],
 ["선택 기능","가드레일은 필요 시 추가하는 선택 기능이며 법률 판단이 아닌 사전 점검. 사람 확인 필요 항목은 담당 부서와 함께 기록"],
 ["실제와 가정의 구분","마지막 장면에서 AI 생성분·코드 계산분·가정치를 1장으로 구분"]].forEach((h,i)=>{
  const col = i%2, row = Math.floor(i/2), x = 0.5 + col*6.2, y = 1.5 + row*2.7;
  s.addShape(pres.ShapeType.roundRect, { x, y, w:6.1, h:2.5, rectRadius:0.08, fill:{ color:C.background2 }, line:{ color:C.background2 }, objectName:`표기카드${i+1}` });
  s.addShape(pres.ShapeType.ellipse, { x:x+0.3, y:y+0.3, w:0.5, h:0.5, fill:{ color:C.accent1 }, line:{ color:C.accent1 } });
  T(s, String(i+1), { x:x+0.3, y:y+0.3, w:0.5, h:0.5, align:"center", valign:"middle", fontSize:16, bold:true, color:C.background1 });
  T(s, h[0], { x:x+1.0, y:y+0.3, w:4.8, h:0.5, fontSize:20, bold:true, valign:"middle" });
  T(s, h[1], { x:x+0.3, y:y+1.05, w:5.5, h:1.3, fontSize:15, color:C.text2 });
});

// ---------- 안 A ----------
const subImg = MODE==="real" ? "화면은 실제 화면 캡처(장면 2~9)와 와이어프레임(그 외)" : "화면은 와이어프레임";
pres.addSection({ title:"안 A: 2030 투자입문자" });
flowSlide("안 A\n2030 투자입문자 신용카드", `요청 입력, 시장조사, 컨셉·검증과 에이전트 간 협의, 디자인·마케팅, 통합 보고서까지 8개 장면에 개별 활용 2개 장면과 클로징을 더해 11개 장면으로 구성. ${subImg}`, A, C.accent1, "안 A: 2030 투자입문자");
A.forEach(sc => sceneSlide(sc, C.accent1, "안 A", "안 A: 2030 투자입문자", A.length, "A"));

// ---------- 안 B ----------
pres.addSection({ title:"안 B: GenZ 특화" });
const subB = MODE==="real" ? "화면은 실제 화면 캡처(장면 1~8)와 와이어프레임(장면 9~10)" : "화면은 와이어프레임";
flowSlide("안 B\nGenZ 특화 신용카드", `투자와 무관한 일반 소비 카드에서도 동일한 에이전트 팀이 협의하며 수행하는 과정을 개별 활용 2개 장면 포함 10개 장면으로 구성. ${subB}. 장면 구성은 초안`, B, C.accent2, "안 B: GenZ 특화");
B.forEach(sc => {
  sceneSlide(sc, C.accent2, "안 B", "안 B: GenZ 특화", B.length, "B");
  if (sc.no==="08") {
    const cs = pres.addSlide({ masterName:"CONTENT", sectionTitle:"안 B: GenZ 특화" });
    cs.addText("안 B 카드 시안: 디자인·마케팅 에이전트 산출물", { placeholder:"title" });
    cs.addImage({ path:`${__dirname}/img/genz-cards.png`, x:0.5, y:1.5, w:8.4, h:4.2, altText:"세칸 카드 시안 3종(NOON, CLEAR, NIGHT)", objectName:"카드시안이미지" });
    label(cs, "시안 구성", 9.2, 1.5, C.accent2);
    T(cs, ["‘세칸’ 세로형 카드 3종: NOON(무광 아이보리), CLEAR(투명 폴리카보네이트), NIGHT(새벽남색 무광)","공통: 세 칸을 은유한 로고 심볼(1칸 라임 포인트), 칩·비접촉 마크, 앞면 혜택 수치·카드 번호 미표기","소재·마감: 엠보싱·금박·미세 인쇄(NOON) / 투명 몸체 위 불투명 인쇄 레이어(CLEAR) / 라임 박 로고(NIGHT)","발급사·네트워크는 자리표시([ISSUER], NETWORK)"].map((t,i,a)=>({ text:t, options:{ bullet:{ indent:16 }, breakLine:i<a.length-1, paraSpaceAfter:8 } })), { x:9.2, y:1.85, w:3.63, h:4.4, fontSize:14, objectName:"시안설명" });
    T(cs, "시안은 보고서 상단 대표 이미지와 시안 비교 섹션에 동일하게 활용", { x:0.5, y:6.0, w:8.4, h:0.4, fontSize:12, color:C.accent5 });
    const cb = pres.addSlide({ masterName:"CONTENT", sectionTitle:"안 B: GenZ 특화" });
    cb.addText("안 B 카드 시안 뒷면: 판정 규칙·보안 정보 배치", { placeholder:"title" });
    cb.addImage({ path:`${__dirname}/img/genz-cards-back.png`, x:0.5, y:1.5, w:8.4, h:4.2, altText:"세칸 카드 시안 3종 뒷면", objectName:"카드뒷면이미지" });
    label(cb, "뒷면 구성", 9.2, 1.5, C.accent2);
    T(cb, ["상단: 카드 번호·유효기간·CVC·소지자명 자리표시(실번호 미사용)","중앙: 서명란, 판정 규칙 한 줄(“직전 3개월 이용액 합계 1위 영역 자동 배정”), 비율 수치 미표기","하단: 분실·도난 안내, 고객센터 자리표시, 네트워크 자리표시","혜택 비율·조건은 뒷면 문구와 앱에서만 안내"].map((t,i,a)=>({ text:t, options:{ bullet:{ indent:16 }, breakLine:i<a.length-1, paraSpaceAfter:8 } })), { x:9.2, y:1.85, w:3.63, h:4.4, fontSize:14, objectName:"뒷면설명" });
    const cr = pres.addSlide({ masterName:"CONTENT", sectionTitle:"안 B: GenZ 특화" });
    cr.addText("안 B 보고서 주요 화면: 핵심 요약과 포지셔닝 맵", { placeholder:"title" });
    const rs = MODE==="real" ? [`${__dirname}/img/shot-B-08c.png`,`${__dirname}/img/shot-B-08d.png`] : [`${__dirname}/img/R-1c.png`,`${__dirname}/img/R-2c.png`];
    rs.forEach((pth,k)=>{
      const x = 0.5 + k*6.2;
      cr.addImage({ path:pth, x, y:1.5, w:6.1, h:3.07, altText:k?"포지셔닝 맵":"핵심 요약", objectName:k?"포지셔닝맵이미지":"핵심요약이미지" });
      cr.addShape(pres.ShapeType.rect, { x, y:1.5, w:6.1, h:3.07, fill:{ color:C.background1, transparency:100 }, line:{ color:"C9D1E3", width:1 } });
      cr.addShape(pres.ShapeType.roundRect, { x:x+0.1, y:1.6, w:(MODE==="real"?1.75:1.45), h:0.3, rectRadius:0.05, fill:{ color:(MODE==="real"?C.accent6:C.accent3) }, line:{ color:(MODE==="real"?C.accent6:C.accent3) } });
      T(cr, MODE==="real"?"실제 화면 캡처":"와이어프레임", { x:x+0.1, y:1.6, w:(MODE==="real"?1.75:1.45), h:0.3, align:"center", valign:"middle", fontSize:12, bold:true });
    });
    label(cr, "핵심 요약 (보고서 최상단)", 0.5, 4.8, C.accent2); label(cr, "포지셔닝 맵", 6.7, 4.8, C.accent2);
    T(cr, ["컨셉, 주요 혜택, 타깃 세그먼트, 차별점을 4개 블록으로 배치","KPI(채택 의향·손익)와 구분별 요약표 병기"].map((t,i,a)=>({ text:t, options:{ bullet:{ indent:16 }, breakLine:i<a.length-1, paraSpaceAfter:6 } })), { x:0.5, y:5.15, w:6.0, h:1.5, fontSize:14, objectName:"핵심요약설명" });
    T(cr, ["경쟁사와 자사 카드 라인업 사이의 신상품 위치 표시, 자사 카드별 타깃 중복도 표 병기","자사 라인업·좌표는 가상 데이터(고객사 카드 DB 연동 후 실제 값 반영)"].map((t,i,a)=>({ text:t, options:{ bullet:{ indent:16 }, breakLine:i<a.length-1, paraSpaceAfter:6 } })), { x:6.7, y:5.15, w:6.1, h:1.5, fontSize:14, objectName:"포지셔닝설명" });

  }
});

// ---------- 화면 구성 샘플 ----------
pres.addSection({ title:"화면 구성 샘플" });
const UI = [
 { f:"UI-1", title:"대화형", sub:"좌측 대화 기록, 중앙 대화·진행 로그 구성",
   cfg:["좌측: 기획 대화 기록 목록, 새 대화 시작","중앙: 요청·에이전트 답변을 대화 형태로 표시","오케스트레이터·에이전트 진행 로그를 대화 내 시간순으로 표시","단계 요약 카드와 ‘보고서로 보기’ 버튼 제공"],
   good:"메신저와 유사한 형태로 신규 사용자의 진입 장벽이 낮음. 사람 확인 단계도 대화 내 버튼으로 처리" },
 { f:"UI-2", title:"연결도형", sub:"대화와 병행해 에이전트 간 연결 구조를 실시간 표시",
   cfg:["좌측: 대화·진행 로그(축소)","우측: 오케스트레이터와 에이전트의 연결 구조도","실행 중·완료·대기를 색으로 구분, 선택 에이전트(가드레일)는 점선","하단에 현재 연결 상태를 한 줄로 요약"],
   good:"에이전트의 동시 수행과 상호 협의를 직관적으로 전달, 시연·설명에 효과적" },
 { f:"UI-3", title:"리포트형", sub:"우측 절반에 신상품기획보고서(HTML) 표시",
   cfg:["좌측: 대화 및 최종 요약","우측 절반: 신상품기획보고서 미리보기","대표 이미지를 제목과 함께 상단 배치","HTML 저장·인쇄 지원"],
   good:"에이전트 결과가 하나의 문서로 통합되어 즉시 검토·보고 가능, 수정 요청은 대화로 반영" },
];
s = pres.addSlide({ masterName:"CONTENT", sectionTitle:"화면 구성 샘플" });
s.addText("사용자 화면 구성 샘플 3종", { placeholder:"title" });
UI.forEach((u,i)=>{
  const x = 0.5 + i*4.17;
  s.addImage({ path:`${__dirname}/img/${u.f}c.png`, x, y:1.6, w:3.98, h:2.0, sizing:{ type:"contain", w:3.98, h:2.0 }, altText:`${u.title} 화면 와이어프레임`, objectName:`화면샘플${i+1}` });
  s.addShape(pres.ShapeType.rect, { x, y:1.6, w:3.98, h:2.0, fill:{ color:C.background1, transparency:100 }, line:{ color:"C9D1E3", width:1 } });
  s.addShape(pres.ShapeType.roundRect, { x:x+0.1, y:1.7, w:1.3, h:0.3, rectRadius:0.05, fill:{ color:C.accent3 }, line:{ color:C.accent3 } });
  T(s, "와이어프레임", { x:x+0.1, y:1.7, w:1.3, h:0.3, align:"center", valign:"middle", fontSize:12, bold:true });
  T(s, `${i+1}. ${u.title}`, { x, y:3.85, w:3.98, h:0.45, fontSize:20, bold:true, color:C.accent4 });
  T(s, u.sub, { x, y:4.35, w:3.98, h:0.8, fontSize:14, color:C.text2 });
});
T(s, "3개 형태의 조합 가능. 현재 시연 화면은 대화형 기반에 연결도·보고서 탭을 결합한 구성", { x:0.5, y:5.8, w:12.3, h:0.5, fontSize:14, color:C.accent5 });
UI.forEach((u,i)=>{
  s = pres.addSlide({ masterName:"SCENE", sectionTitle:"화면 구성 샘플" });
  s.addShape(pres.ShapeType.ellipse, { x:0.5, y:0.35, w:0.95, h:0.95, fill:{ color:C.accent4 }, line:{ color:C.accent4 } });
  T(s, String(i+1), { x:0.5, y:0.35, w:0.95, h:0.95, align:"center", valign:"middle", fontSize:24, bold:true, color:C.background1 });
  s.addText("화면 샘플: " + u.title, { placeholder:"title" });
  s.addShape(pres.ShapeType.roundRect, { x:10.3, y:0.55, w:2.53, h:0.5, rectRadius:0.08, fill:{ color:C.background2 }, line:{ color:C.background2 } });
  T(s, `화면 샘플 · ${i+1} / 3`, { x:10.3, y:0.55, w:2.53, h:0.5, align:"center", valign:"middle", fontSize:12, bold:true, color:C.text2 });
  s.addImage({ path:`${__dirname}/img/${u.f}c.png`, x:0.5, y:1.55, w:IW, h:IH, altText:`${u.title} 화면 와이어프레임`, objectName:"화면이미지(교체)" });
  s.addShape(pres.ShapeType.rect, { x:0.5, y:1.55, w:IW, h:IH, fill:{ color:C.background1, transparency:100 }, line:{ color:"C9D1E3", width:1 } });
  s.addShape(pres.ShapeType.roundRect, { x:0.65, y:1.7, w:1.45, h:0.34, rectRadius:0.05, fill:{ color:C.accent3 }, line:{ color:C.accent3 } });
  T(s, "와이어프레임", { x:0.65, y:1.7, w:1.45, h:0.34, align:"center", valign:"middle", fontSize:12, bold:true });
  s.addShape(pres.ShapeType.rect, { x:0.5, y:5.64, w:IW, h:0.75, fill:{ color:C.text1 }, line:{ color:C.text1 } });
  T(s, u.sub, { x:0.75, y:5.64, w:IW-0.5, h:0.75, valign:"middle", fontSize:14, color:C.background1 });
  label(s, "화면 구성", RX, 1.55, C.accent4);
  T(s, u.cfg.map((t,k)=>({ text:t, options:{ bullet:{ indent:16 }, breakLine:k<u.cfg.length-1, paraSpaceAfter:6 } })), { x:RX, y:1.9, w:RW, h:2.5, fontSize:14 });
  label(s, "기대 효과", RX, 4.5, C.accent4);
  s.addShape(pres.ShapeType.roundRect, { x:RX, y:4.82, w:RW, h:1.88, rectRadius:0.06, fill:{ color:C.background2 }, line:{ color:C.background2 } });
  T(s, u.good, { x:RX+0.18, y:4.92, w:RW-0.36, h:1.7, fontSize:14 });
});

// ---------- 확인 요청 ----------
pres.addSection({ title:"확인 요청" });
s = pres.addSlide({ masterName:"SECTION_DARK", sectionTitle:"확인 요청" });
s.addText("확인 요청 사항", { placeholder:"title" });
const asks = ["시나리오 선택: 안 A(투자 연계 카드) 또는 안 B(GenZ 일반 소비 카드)","영상 길이·시청 대상: 3분대, 현업 담당자 중심 구성 기준 확인","화면 이미지: 와이어프레임 버전과 실제 화면 버전 2종 제공, 공개 가능 범위 확인","사용자 화면 형태: 대화형·연결도형·리포트형 중 선호안 또는 조합 여부","외부 공개 여부: 공개 시 카드명·회사명 비식별 처리","현행 기획 소요 기간: 오프닝 반영용 수치 제공 (미제공 시 수치 없이 진행)"];
T(s, asks.map((t,i)=>({ text:t, options:{ bullet:{ type:"number" }, breakLine:i<asks.length-1, paraSpaceAfter:14 } })), { x:0.8, y:1.9, w:11.7, h:4.3, fontSize:18, color:C.background1 });
T(s, "회신 후 장면 구성·자막 확정, 녹화는 장면별 개별 진행", { x:0.8, y:6.4, w:11.7, h:0.4, fontSize:14, color:C.accent6 });

(async () => {
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("done", OUT);
})();
