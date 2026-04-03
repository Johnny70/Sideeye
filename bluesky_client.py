# ============================================================
# MODULE: bluesky_client
# RESPONSIBILITY: Post articles to Bluesky via the AT Protocol.
# DEPENDS ON: atproto, os (stdlib)
# EXPOSES: post_article(title, link, comment) -> str (post URI)
# ============================================================

import logging
import os
from pathlib import Path

from atproto import AsyncClient
from dotenv import load_dotenv

_ENV_FILE = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_FILE)

logger = logging.getLogger(__name__)

_MAX_TEXT_LENGTH = 290  # Bluesky limit is 300 graphemes; leave margin


def _credentials() -> tuple[str, str]:
    handle   = os.environ.get("BLUESKY_HANDLE", "")
    password = os.environ.get("BLUESKY_APP_PASSWORD", "")
    if not handle or not password:
        raise RuntimeError(
            "BLUESKY_HANDLE och BLUESKY_APP_PASSWORD måste vara satta i .env."
        )
    return handle, password


def _build_text(title: str, link: str, comment: str) -> str:
    """
    Build the post text.
    Uses AI comment if available, otherwise falls back to title.
    Always appends the article link. Truncates to fit within limit.
    """
    body = comment.strip() if comment.strip() else title.strip()

    # Truncate body so body + newlines + link fits within limit
    # 2 newlines + link = len(link) + 2 chars
    max_body = _MAX_TEXT_LENGTH - len(link) - 2
    if len(body) > max_body:
        body = body[: max_body - 1] + "…"

    return f"{body}\n\n{link}"


async def post_article(title: str, link: str, comment: str = "") -> str:
    """
    Log in to Bluesky and post the article.
    Returns the URI of the created post.
    Raises RuntimeError on failure.
    """
    handle, password = _credentials()
    text = _build_text(title, link, comment)

    try:
        client = AsyncClient()
        await client.login(handle, password)
        response = await client.send_post(text=text)
    except Exception as exc:
        logger.error("Bluesky login or post failed: %s", exc)
        raise RuntimeError(f"Bluesky-post misslyckades: {exc}") from exc

    uri: str = response.uri
    logger.info("Posted to Bluesky: %s", uri)
    return uri
