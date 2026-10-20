"""스토리보드 와이어프레임 프레임 + 합성 음성 나레이션으로 데모 영상 시안(mp4)을 만든다.

사용: python3 make_video.py <ffmpeg 경로> <프레임 PNG 폴더> <narr.json> <출력 폴더>
  - 프레임 PNG: A-00(타이틀) A-01.. / B-00 B-01.. (1920x1080)
  - narr.json: {"A":[{no,narr,...}], "B":[...]}  (스토리라인 pptx 생성 데이터)
  - 나레이션은 macOS `say -v Yuna`로 만든다. 장면 길이 = 나레이션 길이 + 여백.
"""
import json, re, subprocess, sys, tempfile
from pathlib import Path

ff, frames, narr_json, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
out.mkdir(parents=True, exist_ok=True)
data = json.loads(narr_json.read_text(encoding="utf-8"))
INTRO = {"A": "카드 신상품 기획 AI 에이전트 데모 영상입니다. 안 에이, 이삼십 투자 입문자 신용카드.",
         "B": "카드 신상품 기획 AI 에이전트 데모 영상입니다. 안 비, 젠지 특화 신용카드."}
NAMES = {"A": "데모영상_안A_2030투자입문자", "B": "데모영상_안B_GenZ특화"}
PAD, FPS = 0.9, 30


def run(*a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr[-1500:])
    return r.stderr


def duration(path):
    err = subprocess.run([ff, "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    h, m, s = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err).groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


for case in ("A", "B"):
    tmp = Path(tempfile.mkdtemp(prefix=f"vid{case}_"))
    items = [("00", INTRO[case])] + [(s["no"], s["narr"]) for s in data[case]]
    clips = []
    for no, text in items:
        aiff, wav, clip = tmp / f"{no}.aiff", tmp / f"{no}.wav", tmp / f"{no}.mp4"
        run("say", "-v", "Yuna", "-r", "170", "-o", str(aiff), text)
        run(ff, "-y", "-hide_banner", "-i", str(aiff), "-ar", "44100", "-ac", "2", str(wav))
        dur = duration(wav) + PAD
        frames_n = int(dur * FPS)
        png = frames / f"{case}-{no}.png"
        vf = (f"zoompan=z='min(zoom+0.00025,1.035)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames_n}:s=1920x1080:fps={FPS},"
              f"fade=t=in:st=0:d=0.4,fade=t=out:st={dur - 0.4:.2f}:d=0.4,format=yuv420p")
        run(ff, "-y", "-hide_banner", "-loop", "1", "-i", str(png), "-i", str(wav),
            "-vf", vf, "-af", f"apad=pad_dur={PAD},afade=t=out:st={dur - 0.4:.2f}:d=0.4", "-t", f"{dur:.2f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-shortest", str(clip))
        clips.append(clip)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{c}'\n" for c in clips))
    dst = out / f"{NAMES[case]}.mp4"
    run(ff, "-y", "-hide_banner", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(dst))
    print(case, dst, f"{duration(dst):.0f}초")
