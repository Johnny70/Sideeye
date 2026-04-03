# ============================================================
# MODULE: news_store
# RESPONSIBILITY: In-memory article cache, feed fetching, SSE broadcast, background poller.
# DEPENDS ON: config, rss_reader, content_filter, interest_scorer, asyncio, json, logging, datetime (stdlib)
# EXPOSES: _cache, _clients, load_feeds, _public_cache, _fetch_all, _broadcast, _rescore_and_broadcast, _poller
# ============================================================

import asyncio
import json
import logging
from datetime import datetime, timezone

from config import FEEDS_FILE, POLL_INTERVAL
from content_filter import apply_filter
from interest_scorer import score_articles
from rss_reader import fetch_feed

logger = logging.getLogger(__name__)

_cache: dict = {
    "articles":     [],
    "raw_articles": [],
    "errors":       [],
    "filtered":     0,
    "total":        0,
    "updated_at":   None,
    "first_run":    False,
}

_clients: set[asyncio.Queue] = set()


def load_feeds() -> list[dict]:
    with FEEDS_FILE.open(encoding="utf-8") as f:
        return json.load(f)["feeds"]


def _public_cache() -> dict:
    """Cache utan raw_articles – används i SSE-broadcast och REST-svar."""
    return {k: v for k, v in _cache.items() if k != "raw_articles"}


async def _fetch_all() -> dict:
    feeds = load_feeds()
    all_articles: list[dict] = []
    errors: list[dict] = []

    for feed in feeds:
        try:
            articles = await fetch_feed(feed["url"])
            for article in articles:
                article["feed_name"] = feed["name"]
                article["category"]  = feed.get("category", "")
            all_articles.extend(articles)
        except RuntimeError as exc:
            errors.append({"feed": feed["name"], "error": str(exc)})

    raw_articles, total_filtered = apply_filter(all_articles)
    scored = score_articles(raw_articles)

    return {
        "total":        len(scored),
        "filtered":     total_filtered,
        "errors":       errors,
        "articles":     scored,
        "raw_articles": raw_articles,
        "updated_at":   datetime.now(timezone.utc).isoformat(),
    }


async def _broadcast(data: dict) -> None:
    msg = json.dumps(data)
    for q in list(_clients):
        await q.put(msg)


async def _rescore_and_broadcast() -> None:
    """Re-score cachade råartiklar mot uppdaterade intressen och pusha till klienter."""
    scored = score_articles(_cache.get("raw_articles", []))
    _cache["articles"] = scored
    _cache["total"] = len(scored)
    await _broadcast(_public_cache())


async def _poller() -> None:
    while True:
        try:
            data = await _fetch_all()
            _cache.update(data)
            await _broadcast(_public_cache())
        except Exception as exc:
            logger.exception("Poller failed: %s", exc)
        await asyncio.sleep(POLL_INTERVAL)
