"""스키마 로딩·검증·LLM용 단일 스키마 만들기. 계약 원본은 agents/_common 과 agents/<n>/ 의 JSON Schema."""
from __future__ import annotations

import copy
import glob
import json
import os
import re
from functools import lru_cache

from .config import AGENT_DIR, AGENTS_DIR

COMMON = os.path.join(AGENTS_DIR, "_common")
load = lambda p: json.load(open(p, encoding="utf-8"))


@lru_cache(maxsize=None)
def _registry():
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
    res = []
    for f in sorted(glob.glob(f"{COMMON}/*.schema.json")):
        d = load(f)
        res.append((os.path.basename(f), Resource.from_contents(d, default_specification=DRAFT202012)))
        if "$id" in d:
            res.append((d["$id"], Resource.from_contents(d, default_specification=DRAFT202012)))
    for f in glob.glob(f"{AGENTS_DIR}/[0-9][0-9]-*/*.schema.json"):
        d = load(f)
        if "$id" in d:
            res.append((d["$id"], Resource.from_contents(d, default_specification=DRAFT202012)))
    for f in glob.glob(f"{AGENTS_DIR}/09-design-marketing/schema/*.schema.json"):
        res.append(("card-studio/agents/design_marketing/schema/" + os.path.basename(f),
                    Resource.from_contents(load(f), default_specification=DRAFT202012)))
    return Registry().with_resources(res)


def agent_schemas(agent: str):
    d = os.path.join(AGENTS_DIR, AGENT_DIR[agent])
    return load(f"{d}/in.schema.json"), load(f"{d}/out.schema.json")


def env_in():
    return load(f"{COMMON}/envelope.in.schema.json")


def env_out():
    return load(f"{COMMON}/envelope.out.schema.json")


def validate_envelope_in(agent: str, env: dict) -> list[dict]:
    """호출 전 입력 검증(00 설계서 6-2). 봉투와 payload 둘 다."""
    a_in, _ = agent_schemas(agent)
    return _errors([("in", env_in(), env), ("in.payload", a_in, env.get("payload", {}))])


def validate_envelope_out(agent: str, env: dict) -> list[dict]:
    """호출 후 출력 검증(6-4 앞 두 단계): 봉투, result."""
    _, a_out = agent_schemas(agent)
    return _errors([("out", env_out(), env), ("out.result", a_out, env.get("result"))])


def _errors(items):
    from jsonschema import Draft202012Validator
    out = []
    for label, schema, data in items:
        for e in Draft202012Validator(schema, registry=_registry()).iter_errors(data):
            out.append({"code": "SCHEMA_INVALID", "path": label + ":" + "/".join(map(str, e.path)), "message": e.message[:200]})
    return out


# ---- LLM 에 강제할 단일 스키마(도구 submit_output 의 input_schema) ----------------------

# sources 는 LLM이 후보를 쓰고 코드가 도구 결과 URL과 대조해 거른다(02 문서 3절). 나머지는 코드만 쓴다.
CODE_OWNED = ["run_id", "request_id", "agent", "contract_version", "model", "input_refs", "usage", "validation"]


def llm_output_schema(agent: str) -> dict:
    """봉투 out 에서 코드가 채우는 필드를 빼고 result 자리에 에이전트 out 스키마를 끼운 자기완결 스키마.
    외부 $ref 는 모두 인라인하고, 로컬 $defs 는 이름이 겹치지 않게 접두사를 붙여 합친다."""
    env = copy.deepcopy(env_out())
    _, a_out = agent_schemas(agent)
    defs = dict(env.get("$defs", {}))
    result = _inline(copy.deepcopy(a_out), f"r_{agent}_", defs, AGENTS_DIR + "/" + AGENT_DIR[agent])
    env["properties"]["result"] = result
    env = _inline(env, "e_", defs, COMMON)
    env["$defs"] = defs
    for k in CODE_OWNED:
        env["properties"].pop(k, None)
    env["required"] = [r for r in env.get("required", []) if r not in CODE_OWNED]
    env.pop("$schema", None)
    env.pop("$id", None)
    return env


def _inline(node, prefix, defs, base_dir):
    """node 안의 $ref 를 처리. '#/$defs/x' 는 defs 로 옮기며 접두사, 파일 참조는 읽어서 인라인."""
    if isinstance(node, dict):
        local = node.pop("$defs", None)
        if local:
            for k, v in local.items():
                defs.setdefault(prefix + k, _inline(v, prefix, defs, base_dir))
        ref = node.get("$ref")
        if ref:
            m = re.match(r"^#/\$defs/(.+)$", ref)
            if m:
                if prefix + m.group(1) not in defs and m.group(1) in defs:
                    return {"$ref": f"#/$defs/{m.group(1)}"}
                return {"$ref": f"#/$defs/{prefix}{m.group(1)}"}
            path, _, frag = ref.partition("#")
            if path:
                target = _find(path, base_dir)
                newprefix = prefix + os.path.basename(path).split(".")[0] + "_"
                sub = _inline(copy.deepcopy(target), newprefix, defs, base_dir)
                m2 = re.match(r"^/\$defs/(.+)$", frag or "")
                if m2:   # 대상 파일의 $defs 는 newprefix 로 defs 에 옮겨졌다. 그 항목을 가리키는 참조만 돌려준다
                    return {"$ref": f"#/$defs/{newprefix}{m2.group(1)}"}
                return sub
        # 안에 끼운 스키마의 $id/$schema 는 참조 기준(base URI)을 바꿔 "#/$defs" 를 깨뜨리므로 뺀다
        return {k: _inline(v, prefix, defs, base_dir) for k, v in node.items() if k not in ("$id", "$schema")}
    if isinstance(node, list):
        return [_inline(v, prefix, defs, base_dir) for v in node]
    return node


def _find(ref_path, base_dir):
    for cand in [os.path.join(base_dir, ref_path), os.path.join(COMMON, os.path.basename(ref_path)),
                 os.path.join(AGENTS_DIR, "09-design-marketing", ref_path)]:
        if os.path.exists(cand):
            return load(cand)
    raise FileNotFoundError(ref_path)
