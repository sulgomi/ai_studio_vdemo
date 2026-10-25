"""웹 검색 CLI(Tavily). 에이전트가 Bash로 부른다.
  python3 -m cardstudio.search_cli search "질의" [--max 8] [--topic general|news] [--days 90] [--depth basic|advanced]
  python3 -m cardstudio.search_cli extract <url> [<url> ...] [--max-chars 20000]
키는 TAVILY_API_KEY 또는 CARDSTUDIO_TAVILY_ENV(파일 경로) 에서 Tavily 키 한 줄만 읽는다. 키 값을 출력하지 않는다."""
import argparse
import json
import sys

from .tools import TavilySearch


def main(argv=None):
    ap = argparse.ArgumentParser(prog="search_cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--max", type=int, default=8)
    s.add_argument("--topic", default=None, choices=[None, "general", "news"])
    s.add_argument("--days", type=int, default=None)
    s.add_argument("--depth", default=None, choices=[None, "basic", "advanced"])
    e = sub.add_parser("extract")
    e.add_argument("urls", nargs="+")
    e.add_argument("--max-chars", type=int, default=20000)
    a = ap.parse_args(argv)
    import urllib.error
    try:
        t = TavilySearch()
        if a.cmd == "search":
            out = t.search(a.query, a.max, topic=a.topic, days=a.days, depth=a.depth)
        else:
            out = [dict(x, raw_content=(x.get("raw_content") or "")[:a.max_chars]) for x in t.extract(a.urls)]
    except urllib.error.HTTPError as e:
        hint = {432: "Tavily 플랜 사용 한도 초과(키 충전·교체 필요)", 401: "키가 잘못됨", 429: "요청 과다, 잠시 후 재시도"}.get(e.code, "")
        json.dump({"error": f"HTTP {e.code}", "hint": hint}, sys.stdout, ensure_ascii=False)
        print()
        sys.exit(2)
    except RuntimeError as e:
        json.dump({"error": str(e)}, sys.stdout, ensure_ascii=False)
        print()
        sys.exit(2)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
