#!/usr/bin/env python3
"""samples/<에이전트>/ 의 입력·출력 샘플이 스키마를 통과하는지 검사한다.
사용: pip install jsonschema && python3 samples/validate.py   (final-mvp 폴더에서)
입력: 공통 봉투(envelope.in) + payload는 에이전트 in.schema.json
출력: 공통 봉투(envelope.out) + result는 에이전트 out.schema.json
"""
import glob, json, os, sys
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load = lambda p: json.load(open(p, encoding="utf-8"))
env_in = load(f"{ROOT}/agents/_common/envelope.in.schema.json")
env_out = load(f"{ROOT}/agents/_common/envelope.out.schema.json")
# envelope.out 이 envelope.in 의 $defs 를 상대 경로로 참조하므로 함께 등록한다
REG = Registry().with_resources([
    ("envelope.in.schema.json", Resource.from_contents(env_in, default_specification=DRAFT202012)),
    ("envelope.out.schema.json", Resource.from_contents(env_out, default_specification=DRAFT202012)),
])
# 에이전트 스키마끼리의 상대 참조(예: 07 in → 07 out 의 $defs)도 $id 로 등록한다
_extra = []
for _f in glob.glob(f"{ROOT}/agents/[0-9][0-9]-*/*.schema.json"):
    _d = load(_f)
    if "$id" in _d:
        _extra.append((_d["$id"], Resource.from_contents(_d, default_specification=DRAFT202012)))
# 09 는 schema/*.json 을 상대 경로로 참조한다 ($id 가 없어 out.schema.json 의 $id 기준 경로로 등록)
for _f in glob.glob(f"{ROOT}/agents/09-design-marketing/schema/*.schema.json"):
    _extra.append(("card-studio/agents/design_marketing/schema/" + os.path.basename(_f),
                   Resource.from_contents(load(_f), default_specification=DRAFT202012)))
REG = REG.with_resources(_extra)
bad = 0

def check(label, schema, data):
    global bad
    errs = sorted(Draft202012Validator(schema, registry=REG).iter_errors(data), key=lambda e: list(e.path))
    if errs:
        bad += 1
        print(f"FAIL {label}")
        for e in errs[:8]:
            print("   -", "/".join(map(str, e.path)) or "(root)", ":", e.message[:160])
    else:
        print(f"ok   {label}")

for d in sorted(glob.glob(f"{ROOT}/samples/[0-9][0-9]-*")):
    name = os.path.basename(d)
    a_in = load(f"{ROOT}/agents/{name}/in.schema.json")
    a_out = load(f"{ROOT}/agents/{name}/out.schema.json")
    i = load(f"{d}/in.sample.json")
    o = load(f"{d}/out.sample.json")
    check(f"{name} in (봉투)", env_in, i)
    check(f"{name} in.payload", a_in, i.get("payload", {}))
    check(f"{name} out (봉투)", env_out, o)
    check(f"{name} out.result", a_out, o.get("result"))
    for f in ("report.sample.html", "chat.sample.json"):
        if not os.path.exists(f"{d}/{f}"):
            bad += 1
            print(f"FAIL {name}: {f} 없음")
sys.exit(1 if bad else 0)
