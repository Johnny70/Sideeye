# ============================================================
# MODULE: tests/test_bluesky_client
# RESPONSIBILITY: Unit tests for bluesky_client module.
# DEPENDS ON: bluesky_client
# ============================================================

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bluesky_client import _build_text, _credentials, post_article


# ── _credentials ─────────────────────────────────────────────────────────────

def test_credentials_raises_when_missing():
    with patch.dict("os.environ", {}, clear=True):
        import os
        os.environ.pop("BLUESKY_HANDLE", None)
        os.environ.pop("BLUESKY_APP_PASSWORD", None)
        with pytest.raises(RuntimeError, match="BLUESKY_HANDLE"):
            _credentials()


def test_credentials_returns_values_when_set():
    with patch.dict("os.environ", {"BLUESKY_HANDLE": "user.bsky.social", "BLUESKY_APP_PASSWORD": "xxxx-xxxx"}):
        handle, password = _credentials()
    assert handle == "user.bsky.social"
    assert password == "xxxx-xxxx"


# ── _build_text ───────────────────────────────────────────────────────────────

def test_build_text_uses_comment_when_provided():
    text = _build_text("Headline", "https://example.com", "Witty comment here.")
    assert text.startswith("Witty comment here.")
    assert "https://example.com" in text


def test_build_text_falls_back_to_title_when_no_comment():
    text = _build_text("Big News Headline", "https://example.com", "")
    assert text.startswith("Big News Headline")
    assert "https://example.com" in text


def test_build_text_truncates_long_body():
    long_comment = "A" * 400
    link = "https://example.com/article"
    text = _build_text("Headline", link, long_comment)
    assert len(text) <= 295  # within Bluesky grapheme limit + margin


def test_build_text_contains_link_on_own_line():
    text = _build_text("Headline", "https://example.com", "Comment.")
    assert "\n\nhttps://example.com" in text


# ── post_article ─────────────────────────────────────────────────────────────

def test_post_article_returns_uri():
    mock_response = MagicMock()
    mock_response.uri = "at://did:plc:test/app.bsky.feed.post/abc123"

    mock_client_instance = AsyncMock()
    mock_client_instance.login = AsyncMock()
    mock_client_instance.send_post = AsyncMock(return_value=mock_response)

    with patch("bluesky_client.AsyncClient", return_value=mock_client_instance), \
         patch.dict("os.environ", {
             "BLUESKY_HANDLE": "user.bsky.social",
             "BLUESKY_APP_PASSWORD": "xxxx-xxxx",
         }):
        uri = asyncio.run(post_article("Test title", "https://example.com", "Witty."))

    assert uri == "at://did:plc:test/app.bsky.feed.post/abc123"


def test_post_article_raises_runtime_error_on_failure():
    mock_client_instance = AsyncMock()
    mock_client_instance.login = AsyncMock(side_effect=Exception("auth failed"))

    with patch("bluesky_client.AsyncClient", return_value=mock_client_instance), \
         patch.dict("os.environ", {
             "BLUESKY_HANDLE": "user.bsky.social",
             "BLUESKY_APP_PASSWORD": "xxxx-xxxx",
         }):
        with pytest.raises(RuntimeError, match="Bluesky-post misslyckades"):
            asyncio.run(post_article("Test title", "https://example.com"))
