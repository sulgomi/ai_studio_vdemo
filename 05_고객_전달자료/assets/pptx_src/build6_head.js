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

