"""실행 기록(trace) 이벤트를 trace.json 에 덧붙인다. 사용: python3 trace.py <event> <agent|-> "<메시지>" """
import json, os, sys
from datetime import datetime, timezone
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trace.json")
ev = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []
ev.append({"seq": len(ev) + 1, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "event": sys.argv[1], "agent": None if sys.argv[2] == "-" else sys.argv[2], "detail": sys.argv[3]})
json.dump(ev, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
