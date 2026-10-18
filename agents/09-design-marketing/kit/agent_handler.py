"""Card design agent — AWS Lambda handler for Amazon Bedrock (Converse API + tool use).

Flow per user message:
  load session -> converse(system, messages, toolConfig) -> while the model calls tools:
  validate (qa.py) -> save / return errors to the model -> converse again -> reply + events.

Events sent to the web page (render on the client, never as raw HTML). The page keeps the latest
strategy / boards / storyboards and re-renders the campaign report (report/report-renderer.js) on each:
  {"type": "strategy", "version": n, "data": marketing_strategy}
  {"type": "boards", "version": n, "data": card_boards}
  {"type": "storyboard", "format": "reels", "version": n, "data": storyboard}   -> page plays it live (player/)
  {"type": "render", "format": "reels", "version": n, "render_job": id|null}      -> MP4 started after approval
  {"type": "needs_human", "tool": name, "errors": [...]}

Environment:
  BEDROCK_MODEL_ID     Claude model ID or inference profile ID enabled in your account/region (required)
  SESSIONS_TABLE       DynamoDB table name, partition key "session_id" (optional; in-memory if unset)
  RENDER_DISPATCH_FN   Lambda that starts a Remotion Lambda render from a storyboard (optional)
"""
from __future__ import annotations

import copy
import json
import os
import uuid
from decimal import Decimal
from pathlib import Path

import qa

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "")
MAX_STEPS = 8          # model turns per user message
MAX_TOOL_RETRIES = 2   # failed validations per tool before handing to a person
HISTORY_LIMIT = 24     # messages kept per session


# ---------------------------------------------------------------- tool config
def build_tool_config() -> dict:
    spec = json.loads((HERE / "tools.json").read_text(encoding="utf-8"))
    tools = []
    for t in spec["tools"]:
        schema = (json.loads((KIT / "schema" / t["schema_file"]).read_text(encoding="utf-8"))
                  if "schema_file" in t else t["inline_schema"])
        schema = {k: v for k, v in schema.items() if k not in ("$schema", "title")}
        tools.append({"toolSpec": {"name": t["name"], "description": t["description"],
                                   "inputSchema": {"json": schema}}})
    return {"tools": tools}


TOOL_CONFIG = build_tool_config()
SYSTEM_TEMPLATE = (KIT / "prompts" / "system_prompt.md").read_text(encoding="utf-8")


def render_system(state: dict) -> str:
    return (SYSTEM_TEMPLATE
            .replace("{{CURRENT_STRATEGY_JSON}}", json.dumps(state.get("strategy") or {}, ensure_ascii=False))
            .replace("{{CURRENT_BOARDS_JSON}}", json.dumps(state.get("boards") or {}, ensure_ascii=False))
            .replace("{{CURRENT_STORYBOARDS_JSON}}", json.dumps(state.get("storyboards") or {}, ensure_ascii=False)))


# ---------------------------------------------------------------- session store
class MemoryStore:
    def __init__(self):
        self.data = {}

    def load(self, sid):
        return copy.deepcopy(self.data.get(sid) or new_state())

    def save(self, sid, state):
        self.data[sid] = copy.deepcopy(state)


class DynamoStore:
    """One item per session. Versions of boards/storyboards are kept in `history` for rollback."""

    def __init__(self, table_name):
        import boto3
        self.table = boto3.resource("dynamodb").Table(table_name)

    def load(self, sid):
        item = self.table.get_item(Key={"session_id": sid}).get("Item")
        return json.loads(item["state"]) if item else new_state()

    def save(self, sid, state):
        self.table.put_item(Item={"session_id": sid, "state": json.dumps(state, ensure_ascii=False)})


def new_state():
    return {"messages": [], "strategy": None, "strategy_version": 0, "boards": None, "boards_version": 0, "storyboards": {}, "story_versions": {},
            "history": [], "retries": {}}


# ---------------------------------------------------------------- render dispatch
def start_render(fmt: str, storyboard: dict, boards: dict) -> str | None:
    fn = os.environ.get("RENDER_DISPATCH_FN")
    if not fn:
        return None
    import boto3
    job = str(uuid.uuid4())
    boto3.client("lambda").invoke(FunctionName=fn, InvocationType="Event",
                                  Payload=json.dumps({"job_id": job, "format": fmt, "storyboard": storyboard,
                                                      "boards": boards}).encode())
    return job


# ---------------------------------------------------------------- tools
def handle_tool(name: str, args: dict, state: dict) -> tuple[dict, dict | None]:
    """Returns (tool_result_json, event_or_None)."""
    try:
        if name == "create_strategy":
            doc, errs = args, qa.check_strategy(args, None)
        elif name == "update_strategy":
            if not state.get("strategy"):
                return {"ok": False, "errors": ["No strategy yet. Call create_strategy first."]}, None
            doc = qa.apply_patch(state["strategy"], args["ops"])
            errs = qa.check_strategy(doc, state.get("boards"))
        elif name == "create_card_boards":
            if not state.get("strategy"):
                return {"ok": False, "errors": ["Write the marketing strategy first (create_strategy); the boards follow it."]}, None
            doc, errs = args, qa.check_boards(args, state["strategy"])
        elif name == "update_card_boards":
            if not state.get("boards"):
                return {"ok": False, "errors": ["No boards yet. Call create_card_boards first."]}, None
            doc = qa.apply_patch(state["boards"], args["ops"])
            errs = qa.check_boards(doc, state.get("strategy"))
        elif name == "create_storyboard":
            if not state.get("boards"):
                return {"ok": False, "errors": ["Create the card boards before any storyboard."]}, None
            doc, errs = args, qa.check_storyboard(args, state["boards"])
        elif name == "render_video":
            sb = state["storyboards"].get(args["format"])
            if not sb:
                return {"ok": False, "errors": [f"No {args['format']} storyboard to render."]}, None
            job = start_render(args["format"], sb, state["boards"])
            v = state["story_versions"].get(args["format"], 1)
            state.setdefault("renders", []).append({"format": args["format"], "version": v, "job": job,
                                                    "approval": args.get("approval_quote", "")})
            return ({"ok": True, "render_job": job, "version": v},
                    {"type": "render", "format": args["format"], "version": v, "render_job": job})
        elif name == "update_storyboard":
            cur = state["storyboards"].get(args["format"])
            if not cur:
                return {"ok": False, "errors": [f"No {args['format']} storyboard yet."]}, None
            doc = qa.apply_patch(cur, args["ops"])
            errs = qa.check_storyboard(doc, state["boards"])
        else:
            return {"ok": False, "errors": [f"Unknown tool {name}."]}, None
    except (KeyError, IndexError, ValueError, TypeError) as e:
        doc, errs = None, [f"Bad patch path or value: {e}"]

    if errs:
        n = state["retries"].get(name, 0) + 1
        state["retries"][name] = n
        if n > MAX_TOOL_RETRIES:
            return ({"ok": False, "errors": errs, "stop": "Validation failed repeatedly; a person will review. Tell the customer briefly."},
                    {"type": "needs_human", "tool": name, "errors": errs})
        return {"ok": False, "errors": errs}, None

    state["retries"][name] = 0
    if name.endswith("strategy"):
        if state.get("strategy"):
            state["history"].append({"kind": "strategy", "version": state["strategy_version"], "data": state["strategy"]})
        state["strategy"] = doc
        state["strategy_version"] = state.get("strategy_version", 0) + 1
        return {"ok": True, "version": state["strategy_version"]}, {"type": "strategy", "version": state["strategy_version"], "data": doc}
    if name.endswith("card_boards"):
        if state.get("boards"):
            state["history"].append({"kind": "boards", "version": state["boards_version"], "data": state["boards"]})
        state["boards"] = doc
        state["boards_version"] += 1
        # storyboards follow the boards by variant code; re-render them with the new look
        return {"ok": True, "version": state["boards_version"]}, {"type": "boards", "version": state["boards_version"], "data": doc}

    fmt = doc["format"]
    if fmt in state["storyboards"]:
        state["history"].append({"kind": "storyboard", "format": fmt, "version": state["story_versions"].get(fmt, 0),
                                 "data": state["storyboards"][fmt]})
    state["storyboards"][fmt] = doc
    state["story_versions"][fmt] = state["story_versions"].get(fmt, 0) + 1
    # no render here: the page previews the storyboard live; MP4 waits for render_video after approval
    return ({"ok": True, "version": state["story_versions"][fmt], "preview": "live"},
            {"type": "storyboard", "format": fmt, "version": state["story_versions"][fmt], "data": doc})


# ---------------------------------------------------------------- conversation loop
def _trim(messages):
    if len(messages) <= HISTORY_LIMIT:
        return messages
    cut = messages[-HISTORY_LIMIT:]
    # never start on a toolResult (its toolUse would be gone): advance to a plain user text turn
    while cut and not (cut[0]["role"] == "user" and any("text" in b for b in cut[0]["content"])):
        cut = cut[1:]
    return cut


def run_turn(session_id: str, user_text: str, client=None, store=None) -> dict:
    if client is None:
        import boto3
        client = boto3.client("bedrock-runtime")
    store = store or STORE
    state = store.load(session_id)
    state["retries"] = {}
    messages = state["messages"] + [{"role": "user", "content": [{"text": user_text}]}]
    events, reply = [], ""

    for _ in range(MAX_STEPS):
        resp = client.converse(
            modelId=MODEL_ID,
            system=[{"text": render_system(state)}],
            messages=messages,
            toolConfig=TOOL_CONFIG,
            inferenceConfig={"maxTokens": 8000, "temperature": 0.7},
        )
        msg = resp["output"]["message"]
        messages.append(msg)
        reply = "".join(b.get("text", "") for b in msg["content"])
        if resp.get("stopReason") != "tool_use":
            break
        results = []
        for block in msg["content"]:
            if "toolUse" not in block:
                continue
            tu = block["toolUse"]
            out, ev = handle_tool(tu["name"], tu["input"], state)
            if ev:
                events.append(ev)
            results.append({"toolResult": {"toolUseId": tu["toolUseId"], "content": [{"json": out}],
                                           "status": "success" if out.get("ok") else "error"}})
        messages.append({"role": "user", "content": results})

    state["messages"] = _trim(messages)
    store.save(session_id, state)
    return {"reply": reply, "events": events}


STORE = DynamoStore(os.environ["SESSIONS_TABLE"]) if os.environ.get("SESSIONS_TABLE") else MemoryStore()


# ---------------------------------------------------------------- Lambda entry (API Gateway WebSocket)
def _jsonable(o):
    if isinstance(o, Decimal):
        return float(o)
    raise TypeError


def lambda_handler(event, context):
    body = json.loads(event.get("body") or "{}")
    sid = body.get("session_id") or event["requestContext"]["connectionId"]
    result = run_turn(sid, body["message"])
    rc = event.get("requestContext", {})
    if rc.get("connectionId"):
        import boto3
        api = boto3.client("apigatewaymanagementapi", endpoint_url=f"https://{rc['domainName']}/{rc['stage']}")
        for ev in result["events"]:
            api.post_to_connection(ConnectionId=rc["connectionId"], Data=json.dumps(ev, ensure_ascii=False, default=_jsonable).encode())
        api.post_to_connection(ConnectionId=rc["connectionId"],
                               Data=json.dumps({"type": "reply", "text": result["reply"]}, ensure_ascii=False).encode())
    return {"statusCode": 200, "body": json.dumps({"ok": True})}
