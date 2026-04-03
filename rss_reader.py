# ============================================================
# MODULE: rss_reader
# RESPONSIBILITY: Fetch and parse a single RSS feed URL into a list of article dicts.
# DEPENDS ON: feedparser, httpx, python-dateutil
# EXPOSES: fetch_feed(url, timeout) -> list[dict]
# ============================================================

import logging

import feedparser
import httpx
from dateutil import parser as dateparser

logger = logging.getLogger(__name__)

# Expected keys in each returned article dict:
#   title        : str   – article headline
#   link         : str   – URL to original article
#   summary      : str   – short description (may be empty)
#   published_at : str | None – ISO 8601 datetime string, or None
#   source_url   : str   – the feed URL that was fetched


def _parse_date(entry: dict) -> str | None:
    """Return the first parseable date field from a feedparser entry as ISO 8601, or None."""
    for attr in ("published", "updated"):
        raw: str | None = entry.get(attr)
        if not raw:
            continue
        try:
            return dateparser.parse(raw).isoformat()
        except Exception as exc:
            logger.warning("Could not parse date %r from feed entry: %s", raw, exc)
            return raw
    return None


async def fetch_feed(url: str, timeout: int = 10) -> list[dict]:
    """
    Fetch and parse an RSS feed at `url`.

    Returns a list of article dicts. Raises RuntimeError on HTTP failure.
    feedparser errors are treated as an empty list with a logged warning.
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            content: bytes = response.content
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Kunde inte hämta feed {url!r}: {exc}") from exc

    parsed = feedparser.parse(content)

    if parsed.get("bozo") and not parsed.entries:
        logger.warning("feedparser reported a malformed feed at %r: %s", url, parsed.get("bozo_exception"))

    articles: list[dict] = []
    for entry in parsed.entries:
        articles.append(
            {
                "title":        entry.get("title", "").strip(),
                "link":         entry.get("link", ""),
                "summary":      entry.get("summary", "").strip(),
                "published_at": _parse_date(entry),
                "source_url":   url,
            }
        )

    logger.debug("Fetched %d articles from %r", len(articles), url)
    return articles
