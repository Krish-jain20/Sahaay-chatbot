"""Web search answer for questions no verified record covers. Shared by chat and Compare.

The answer is always unverified: the card carries the label, the search date, and sources, a source
is "official" only if its exact host is in allowlist.json, and the text has no links, no identity
numbers, and passes the forbidden-claim check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from app.data.loader import Catalog
from app.data.models import Lang
from app.llm.client import LLM, BudgetExceeded, LLMError, RateLimited
from app.safety.allowlist import is_allowed
from app.safety.claims import find_violations
from app.safety.pii import mask_pii

_URL = re.compile(r"https?://\S+|www\.\S+")
MAX_SOURCES = 6
GOV_SUFFIXES = (".gov.in", ".nic.in")


@dataclass
class WebResult:
    text: str = ""
    card: dict[str, Any] | None = None
    blocked: bool = False  # an answer existed but failed the safety check


def _host(source: dict[str, str]) -> str:
    """Grounding titles are the site's domain; otherwise fall back to the link's host."""
    title = source.get("title", "").strip().lower()
    if re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", title):
        return title
    return (urlparse(source.get("url", "")).hostname or "").lower()


def web_card(raw_sources: list[dict[str, str]], catalog: Catalog, today: str) -> dict[str, Any]:
    """Sources deduplicated by host, each marked official only on an exact allowlist host."""
    seen: set[str] = set()
    sources: list[dict[str, Any]] = []
    for src in raw_sources:
        host = _host(src)
        if not host or host in seen:
            continue
        seen.add(host)
        sources.append(
            {
                "n": len(sources) + 1,
                "title": host,
                "url": src["url"],
                "official": (official := is_allowed(f"https://{host}/", catalog.allowlist)),
                # A .gov.in suffix alone is not proof (CLAUDE.md), so it is only ever "not yet checked".
                "kind": "official"
                if official
                else ("gov_unchecked" if host.endswith(GOV_SUFFIXES) else "other"),
            }
        )
    return {"type": "web", "retrieved_on": today, "sources": sources[:MAX_SOURCES]}


def run_web_search(
    llm: LLM, catalog: Catalog, question: str, lang: Lang, user_id: str, today: str
) -> WebResult:
    try:
        ans = llm.web_search(question, lang, user_id=user_id)
    except (RateLimited, BudgetExceeded, LLMError):
        ans = None
    text = _URL.sub("", mask_pii(ans.text)[0]).strip() if ans else ""
    if not text:
        return WebResult()
    if find_violations(text):
        return WebResult(blocked=True)
    return WebResult(text=text, card=web_card(ans.sources, catalog, today))

