#!/usr/bin/env python3
"""기록 만들기 도우미. 오케스트레이터를 기록 모드로 돌려, 기록(out.json)이 없는 단계에서 멈추고 그 단계의 입력과 실행 안내를 낸다.
LLM 단계는 하위 에이전트(또는 API)가 out.json 을 채우고, 사람이 아니라 코드가 검증한다. 채운 뒤 다시 실행하면 앞 단계는 재생되고 다음 단계에서 멈춘다.

  python3 record.py [--h2 N] [--run-id ID]      다음 빈 단계를 찾는다(없으면 끝까지 재생하고 요약을 낸다)
  python3 record.py prompt <stage>              그 단계를 수행할 에이전트용 지시문을 낸다"""
import json, os, shutil, subprocess, sys
MVP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCEN = os.environ.get("RECORD_SCENARIO", "genz-credit-v2")      # 기록할 시나리오 폴더 이름(대안 분기는 genz-credit-v2-alt)
H = os.path.join(MVP, "scenarios", SCEN)
PY = os.environ.get("CARDSTUDIO_PY", sys.executable)
SCRATCH = "/private/tmp/claude-501/-Users-sul-Workspace-ai-studio/9ea57029-1a10-4855-9ae6-5f37dd0e11d1/scratchpad"
AGENT = {"01-research-lead": "research_lead", "02-trend": "trend", "02-trend-evidence": "trend", "03-competitor": "competitor", "04-consumer": "consumer",
         "05-whitespace": "whitespace", "06-concept": "concept", "07-validation": "validation", "08-guardrail": "guardrail",
         "09-design-marketing": "design_marketing", "10-plan-doc": "plan_doc"}
FOLDER = {"research_lead": "01-research-lead", "trend": "02-trend", "competitor": "03-competitor", "consumer": "04-consumer", "whitespace": "05-whitespace",
          "concept": "06-concept", "validation": "07-validation", "guardrail": "08-guardrail", "design_marketing": "09-design-marketing", "plan_doc": "10-plan-doc"}
MODEL = {"09-design-marketing": "opus"}


def export(run_dir, stage):
    """in.json 과, 그 단계가 읽는 부수 파일(평가·시뮬레이션 결과)을 시나리오 폴더로 복사한다. 하네스 검증기가 같은 폴더를 본다."""
    dst = os.path.join(H, stage)
    os.makedirs(dst, exist_ok=True)
    shutil.copy(os.path.join(run_dir, stage, "in.json"), os.path.join(dst, "in.json"))
    for st in os.listdir(run_dir):
        sp = os.path.join(run_dir, st)
        if os.path.isdir(sp):
            os.makedirs(os.path.join(H, st), exist_ok=True)
            import glob
            for src in glob.glob(os.path.join(sp, "eval*.json")) + glob.glob(os.path.join(sp, "twin*.json")) + glob.glob(os.path.join(sp, "in.attempt*.json")):
                shutil.copy(src, os.path.join(H, st, os.path.basename(src)))      # 평가·시뮬레이션 결과와 재작업 입력은 항상 최신으로
            for f in ("out.json", "in.json"):
                src, tgt = os.path.join(sp, f), os.path.join(H, st, f)
                if os.path.exists(src) and ((f == "out.json" and not os.path.exists(tgt)) or (f == "in.json" and st != stage and not os.path.exists(tgt))):
                    shutil.copy(src, tgt)
    for f in ("areas.json",):
        if os.path.exists(os.path.join(run_dir, f)) and not os.path.exists(os.path.join(H, f)):
            shutil.copy(os.path.join(run_dir, f), os.path.join(H, f))


def prompt(stage, extra=""):
    ag = AGENT[stage]
    d = FOLDER.get(ag, stage)
    base = f"/Users/sul/Workspace/ai-studio/final-mvp"
    return f"""당신은 카드 상품기획 에이전트 서비스의 '{stage}' 에이전트({ag}) 역할을 실제로 한 번 수행한다(LLM 단계 실행). 한국어.

읽을 것(모두 {base}/ 아래):
1. agents/_common/common_rules.prompt.md (공통 규칙)
2. agents/{d}/system_prompt.md (당신의 지시문. 규칙을 그대로 따른다), agents/{d}/설계서.md, agents/{d}/in.schema.json, agents/{d}/out.schema.json
3. agents/_common/envelope.out.schema.json (출력 봉투)
4. 입력 봉투: scenarios/{SCEN}/{stage}/in.json  ← payload 에 이번 호출의 모든 근거가 들어 있다
5. 형식 참고용 이전 기록(내용은 베끼지 않는다): scenarios/genz-credit/{d if stage != '02-trend-evidence' else stage}/out.json

할 일: 입력 봉투를 보고 출력 봉투(JSON)를 scenarios/{SCEN}/{stage}/out.json 에 쓴다.
- 입력(payload)에 있는 자료만 근거로 쓴다. 웹 검색은 하지 않는다. 입력에 없는 수치·출처·사실을 만들지 않는다.
- 봉투: run_id/request_id/agent/contract_version 은 입력에서 복사, model 은 "{MODEL.get(stage, 'claude-sonnet-5-5')}", status ok, answer 3문장 이내, result, findings/sources/assumptions/unresolved/limits/clarifications/out_of_scope/followups/input_refs 를 envelope.out.schema.json 에 맞춰 채운다(코드 전용 필드 usage, validation 은 쓰지 않는다). sources 는 payload 에 주어진 출처(docs 등)를 그대로 옮긴다.
- 쓰기 범위: 위 out.json 하나만 만들거나 고친다. 스크래치가 필요하면 {SCRATCH}/ 아래 '{stage.replace('-', '')}_' 로 시작하는 이름만 쓴다. 다른 파일 수정 금지.
{extra}
검증(반드시 실행해 통과시킬 것):
 cd {base} && PYTHONPATH=runtime {SCRATCH}/venv2/bin/python -W ignore -m cardstudio.validate_cli {ag} scenarios/{SCEN}/{stage}/in.json scenarios/{SCEN}/{stage}/out.json
 cd {base}/scenarios/{SCEN} && {SCRATCH}/venv2/bin/python -W ignore harness.py validate {stage}
둘 다 ok:true 가 될 때까지 out.json 을 고친다. 검증기가 불합리하게 막으면 코드를 고치지 말고 최종 보고에 어떤 규칙이 왜 막는지 적는다.
최종 보고: 'DONE {stage} validate=ok|fail' 한 줄과 막힌 규칙이 있으면 짧게."""


def main():
    a = sys.argv[1:]
    if a and a[0] == "prompt":
        print(prompt(a[1], " ".join(a[2:])))
        return 0
    h2 = []
    if "--h2" in a:
        h2 = ["--h2", a[a.index("--h2") + 1]]
    rid = a[a.index("--run-id") + 1] if "--run-id" in a else "v2rec"
    env = dict(os.environ, PYTHONPATH=os.path.join(MVP, "runtime"))
    shutil.rmtree(os.path.join(MVP, "runs", rid), ignore_errors=True)
    r = subprocess.run([PY, "-W", "ignore", "-m", "cardstudio", "run", "--scenario", SCEN, "--record", "--run-id", rid] + h2,
                       cwd=MVP, env=env, capture_output=True, text=True)
    if r.returncode == 3:
        p = json.loads(r.stdout.strip().splitlines()[-1])
        if p.get("rotate"):      # 재작업이 더 필요하다: 지금의 out.json 을 시도 기록으로 돌리고 새 out.json 을 받는다. 다시 실행하면 새 입력이 나온다
            src, dst = p["rotate"]
            shutil.move(src, dst)
            print(json.dumps({"rotated": os.path.relpath(dst, H)}, ensure_ascii=False))
            return main()
        for st in [p["pending_stage"]] + p.get("also_pending", []):
            export(p["run_dir"], st)
            os.makedirs(os.path.join(H, "prompts"), exist_ok=True)
            open(os.path.join(H, "prompts", f"{st}.md"), "w", encoding="utf-8").write(prompt(st))
        print(json.dumps({"pending": [p["pending_stage"]] + p.get("also_pending", []), "run_dir": p["run_dir"]}, ensure_ascii=False))
        return 3
    print(r.stdout[-3000:] if r.returncode == 0 else r.stderr[-3000:])
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
