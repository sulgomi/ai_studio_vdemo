"""에이전트 도구 3개(agents/_common/tools.schema.json). 로컬은 코드 함수, AWS 이관 시 AgentCore Gateway 뒤 도구로 교체.
검색 백엔드는 아직 정하지 않았다(PM 결정 필요): SearchBackend 하나만 구현하면 web_search 가 살아난다."""
from __future__ import annotations

import json
import os
import re
from urllib.parse import urlparse
from typing import Protocol

from .config import AGENT_TOOLS
from .contracts import load, COMMON
from .llm.base import ToolSpec


class SearchBackend(Protocol):
    def search(self, query: str, max_results: int) -> list[dict]:
        """[{title, url, publisher, snippet, published(없으면 None)}]"""


class NotConfigured:
    def search(self, query: str, max_results: int) -> list[dict]:
        raise RuntimeError("web_search 백엔드가 연결되지 않았다(SearchBackend 구현 필요)")


TAVILY_ENV_FILE_VAR = "CARDSTUDIO_TAVILY_ENV"


def tavily_key() -> str | None:
    """TAVILY_API_KEY 만 읽는다. 순서: 환경변수 → (config.load_env 가 읽은 runtime/.env) → CARDSTUDIO_TAVILY_ENV 가 가리키는 파일.
    다른 프로젝트의 .env 에는 다른 키도 있으므로 그 파일에서는 이 키 한 줄만 꺼내고 나머지는 읽지도 보관하지도 않는다."""
    if os.environ.get("TAVILY_API_KEY"):
        return os.environ["TAVILY_API_KEY"]
    path = os.environ.get(TAVILY_ENV_FILE_VAR)
    if path and os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            if line.startswith("TAVILY_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'") or None
    return None


class TavilySearch:
    """Tavily REST(https://docs.tavily.com). 의존 라이브러리 없이 urllib 만 쓴다. 키: TAVILY_API_KEY.
    published 는 Tavily 가 날짜를 주는 경우(뉴스 토픽)에만 채우고, 없으면 None(SRC-3: 지어내지 않음)."""

    URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str | None = None, depth: str = "basic", topic: str = "general", http=None):
        self.key = api_key or tavily_key()
        if not self.key and http is None:
            raise RuntimeError("TAVILY_API_KEY 가 없다(runtime/.env 에 넣는다)")
        self.depth, self.topic, self.http = depth, topic, http or self._post

    def _post(self, payload: dict) -> dict:
        import urllib.request
        req = urllib.request.Request(self.URL, data=json.dumps(payload).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.key}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    def extract(self, urls: list[str]) -> list[dict]:
        """URL 본문 추출(Tavily /extract). 인용은 이 본문에서 확인한다."""
        import urllib.request
        req = urllib.request.Request("https://api.tavily.com/extract", data=json.dumps({"urls": urls}).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.key}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode("utf-8"))
        return [{"url": x.get("url"), "raw_content": x.get("raw_content", "")} for x in d.get("results", [])] + \
               [{"url": x.get("url"), "error": "extract failed"} for x in d.get("failed_results", [])]

    def search(self, query: str, max_results: int = 5, *, topic: str | None = None, days: int | None = None, depth: str | None = None) -> list[dict]:
        payload = {"query": query, "max_results": max(1, min(int(max_results), 10)), "search_depth": depth or self.depth,
                   "topic": topic or self.topic, "include_answer": False}
        if days and payload["topic"] == "news":
            payload["days"] = days
        data = self.http(payload)
        out = []
        for r in data.get("results", []):
            url = r.get("url")
            if not url:
                continue
            out.append({"title": r.get("title", ""), "url": url, "publisher": re.sub(r"^www\.", "", urlparse(url).netloc),
                        "snippet": (r.get("content") or "")[:1200], "published": (r.get("published_date") or None), "score": r.get("score")})
        return out


def make_search() -> "SearchBackend":
    """키가 있으면 Tavily, 없으면 미연결(호출 시 명확한 오류)."""
    return TavilySearch() if tavily_key() else NotConfigured()


class CompetitorDB:
    """03 경쟁사의 card_info_lookup 1순위(DB). 지금은 시장 카드 34종 JSON, 이후 사내 DB/공시 수집분으로 교체."""

    def __init__(self, cards: list[dict]):
        self.cards = cards

    def lookup(self, issuer: str, product_name: str | None = None, **_) -> dict:
        rows = [c for c in self.cards if issuer in (c.get("issuer"), "자사") and (not product_name or product_name in c["name"])]
        return {"found": bool(rows), "path": "db", "records": rows, "missing_fields": [], "conflicts": [],
                "source": "competitor_db"}


def fetch_page(url: str, max_chars: int = 20000, timeout: int = 30) -> dict:
    """URL 본문 텍스트(HTML 태그 제거). 요약 모델을 거치지 않으므로 quote 대조에 쓴다. http(s)만 허용."""
    import html as _html
    import urllib.request
    if not re.match(r"^https?://", url):
        return {"url": url, "text": "", "error": "http(s) URL 만 가져온다"}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (card-studio research)"})
        raw = urllib.request.urlopen(req, timeout=timeout).read()
    except Exception as e:   # 도구 실패는 모델에게 알려 다른 길을 찾게 한다
        return {"url": url, "text": "", "error": f"{type(e).__name__}: {str(e)[:120]}"}
    for enc in ("utf-8", "euc-kr", "cp949"):
        try:
            txt = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        txt = raw.decode("utf-8", "ignore")
    txt = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", txt)
    txt = _html.unescape(re.sub(r"(?s)<[^>]+>", " ", txt))
    txt = re.sub(r"\s+", " ", txt).strip()
    return {"url": url, "text": txt[:max_chars], "error": None}


def build_tools(agent: str, *, search: SearchBackend | None = None, db: CompetitorDB | None = None, kb=None, names: list[str] | None = None) -> list[ToolSpec]:
    schema = load(f"{COMMON}/tools.schema.json")["$defs"]
    search = search or NotConfigured()
    impl = {
        "web_search": lambda a: {"results": search.search(a["query"], a.get("max_results", 5))},
        "card_info_lookup": lambda a: (db.lookup(**a) if db else {"found": False, "path": "db", "records": [], "missing_fields": [], "conflicts": [], "source": "none"}),
        "kb_search": lambda a: ({"results": kb.search(a["query"])} if kb else {"results": []}),
        "web_fetch": lambda a: fetch_page(a["url"], a.get("max_chars", 20000)),
    }
    desc = {"web_search": "공개 웹 검색. 결과의 url 만 출처로 쓸 수 있다.", "card_info_lookup": "카드 상품 정보 조회(DB→공시→웹 순).",
            "kb_search": "내부 지식베이스 검색(고객사 문서).", "web_fetch": "URL 본문 텍스트를 직접 가져온다(인용 대조용)."}
    return [ToolSpec(n, desc[n], schema[n]["properties"]["input"], impl[n]) for n in (names if names is not None else AGENT_TOOLS.get(agent, []))]
