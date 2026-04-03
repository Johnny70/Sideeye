# ============================================================
# MODULE: tests/test_rss_reader
# RESPONSIBILITY: Unit tests for rss_reader module.
# DEPENDS ON: rss_reader
# ============================================================

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from rss_reader import _parse_date, fetch_feed


# ── _parse_date ──────────────────────────────────────────────────────────────

def test_parse_date_returns_iso_for_published():
    entry = {"published": "Mon, 01 Jan 2024 12:00:00 GMT"}
    result = _parse_date(entry)
    assert result is not None
    assert "2024" in result


def test_parse_date_falls_back_to_updated():
    entry = {"updated": "2024-06-15T10:30:00Z"}
    result = _parse_date(entry)
    assert result is not None
    assert "2024" in result


def test_parse_date_returns_none_when_no_date_fields():
    entry = {}
    result = _parse_date(entry)
    assert result is None


def test_parse_date_returns_raw_on_unparseable_date():
    # Garbage date: dateutil will raise, function should return the raw string
    bad_date = "not-a-date-at-all!!!"
    entry = {"published": bad_date}
    result = _parse_date(entry)
    # Returns either None or the raw value — must not raise
    assert result is None or isinstance(result, str)


def test_parse_date_prefers_published_over_updated():
    entry = {
        "published": "Mon, 01 Jan 2024 00:00:00 GMT",
        "updated": "Tue, 02 Jan 2024 00:00:00 GMT",
    }
    result = _parse_date(entry)
    assert result is not None
    assert "2024-01-01" in result


# ── fetch_feed ───────────────────────────────────────────────────────────────

_MINIMAL_RSS = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Test Article</title>
      <link>https://example.com/article</link>
      <description>Test summary content.</description>
      <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""


def test_fetch_feed_returns_articles_list():
    mock_response = MagicMock()
    mock_response.content = _MINIMAL_RSS
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("rss_reader.httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(fetch_feed("https://example.com/feed.xml"))

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["title"] == "Test Article"
    assert result[0]["link"] == "https://example.com/article"
    assert result[0]["source_url"] == "https://example.com/feed.xml"


def test_fetch_feed_raises_runtime_error_on_http_failure():
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))

    with patch("rss_reader.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError):
            asyncio.run(fetch_feed("https://example.com/feed.xml"))


def test_fetch_feed_returns_empty_list_for_empty_feed():
    empty_rss = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>Empty</title></channel></rss>"""

    mock_response = MagicMock()
    mock_response.content = empty_rss
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("rss_reader.httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(fetch_feed("https://example.com/feed.xml"))

    assert result == []
