#!/usr/bin/env python3
"""samples/<에이전트>/ → ui/samples.js (사용자 뷰 개별 에이전트 모드용) + samples/index.html(목록).
사용: python3 samples/build_samples.py   (final-mvp 폴더에서. 샘플을 고친 뒤 다시 실행)
"""
import glob, html, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = {"01": "Sonnet", "02": "Sonnet", "03": "Haiku", "04": "Haiku", "05": "Sonnet", "06": "Sonnet",
         "07": "Sonnet", "08": "Sonnet", "09": "Opus", "10": "Sonnet"}
NAME = {"01": "시장조사 총괄", "02": "트렌드", "03": "경쟁사", "04": "소비자", "05": "시장기회",
        "06": "CVP·컨셉", "07": "시장성 검증", "08": "가드레일", "09": "디자인·마케팅", "10": "기획서"}
out, rows = [], []
for d in sorted(glob.glob(f"{ROOT}/samples/[0-9][0-9]-*")):
    folder = os.path.basename(d); n = folder[:2]
    chat = json.load(open(f"{d}/chat.sample.json", encoding="utf-8"))
    rep = open(f"{d}/report.sample.html", encoding="utf-8").read()
    out.append({"n": n, "folder": folder, "name": NAME[n], "model": MODEL[n], "chat": chat, "report": rep})
    rows.append(f'<tr><td>{n}</td><td>{html.escape(NAME[n])}</td><td>{MODEL[n]}</td>'
                f'<td>{html.escape(chat.get("request",""))}</td>'
                f'<td><a href="{folder}/report.sample.html">리포트</a> · <a href="{folder}/in.sample.json">in</a> · '
                f'<a href="{folder}/out.sample.json">out</a> · <a href="{folder}/chat.sample.json">대화</a></td></tr>')
js = "window.SAMPLES=" + json.dumps(out, ensure_ascii=False).replace("</", "<\\/") + ";\n"
open(f"{ROOT}/ui/samples.js", "w", encoding="utf-8").write(js)
page = ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>에이전트별 샘플</title><style>body{font:15px/1.6 system-ui,"Noto Sans KR",sans-serif;margin:0;background:#f6f4ef;color:#1d2421}'
        'main{max-width:1000px;margin:0 auto;padding:32px 20px}table{border-collapse:collapse;width:100%;background:#fffefb}'
        'th,td{text-align:left;padding:10px 12px;border-bottom:1px solid #e3dfd6;vertical-align:top}th{font-size:12px;color:#69716c}'
        'a{color:#1f6b60}</style></head><body><main><h1>에이전트별 단독 실행 샘플</h1>'
        '<p>리허설 기록을 재료로 만든 샘플입니다. 각 에이전트의 입력·출력은 스키마 검증(<code>python3 samples/validate.py</code>)을 통과합니다. '
        '화면 재생은 <a href="../ui/user-view.html">사용자 뷰</a>의 “개별 에이전트” 모드에서 합니다.</p>'
        '<table><tr><th>#</th><th>에이전트</th><th>모델</th><th>샘플 요청</th><th>파일</th></tr>' + "".join(rows) +
        '</table></main></body></html>')
open(f"{ROOT}/samples/index.html", "w", encoding="utf-8").write(page)
print(f"완료: 에이전트 {len(out)}개 → ui/samples.js, samples/index.html")
