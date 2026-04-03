# ============================================================
# MODULE: llm_client
# RESPONSIBILITY: Generate witty AI comments on news articles via DeepInfra.
# DEPENDS ON: httpx, os, json, pathlib (stdlib)
# EXPOSES: generate_comment(title, summary) -> str
# ============================================================

import json
import logging
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

_ENV_FILE = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_FILE)

logger = logging.getLogger(__name__)

_API_URL       = "https://api.deepinfra.com/v1/openai/chat/completions"
_MODEL         = "meta-llama/Meta-Llama-3.1-8B-Instruct"
_SETTINGS_FILE = Path(__file__).parent / "settings.json"

_DEFAULT_PROMPT = (
    "You are a sharp, witty news commentator with a dry sense of humor. "
    "When given a news headline and summary, respond with a single short comment "
    "(1–2 sentences max). Be clever, occasionally sardonic, never cruel. "
    "Do not repeat the headline. Do not use hashtags or emojis. "
    "Write in English."
)
_DEFAULT_TEMPERATURE = 0.85


def _api_key() -> str:
    key = os.environ.get("DEEPINFRA_API_KEY", "")
    if not key:
        raise RuntimeError(
            f"DEEPINFRA_API_KEY is not set. Looked for .env at: {_ENV_FILE}"
        )
    return key


def _load_settings() -> tuple[str, float]:
    """Load system prompt and temperature from settings.json. Falls back to defaults."""
    try:
        with _SETTINGS_FILE.open(encoding="utf-8") as f:
            data = json.load(f)
        prompt      = data.get("system_prompt", _DEFAULT_PROMPT)
        temperature = float(data.get("temperature", _DEFAULT_TEMPERATURE))
        return prompt, temperature
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        logger.warning("Could not load settings.json, using defaults: %s", exc)
        return _DEFAULT_PROMPT, _DEFAULT_TEMPERATURE


async def generate_comment(title: str, summary: str) -> str:
    """
    Call DeepInfra's Llama 3.1 8B to generate a witty one-liner about the article.
    Raises RuntimeError on API or network failure.
    """
    system_prompt, temperature = _load_settings()

    user_message = f"Headline: {title}"
    if summary:
        user_message += f"\nSummary: {summary[:400]}"

    payload = {
        "model": _MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        "max_tokens": 120,
        "temperature": temperature,
    }

    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(_API_URL, json=payload, headers=headers)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"DeepInfra API request failed: {exc}") from exc

    data = response.json()
    try:
        comment: str = data["choices"][0]["message"]["content"].strip().strip('"').strip("'")
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected API response structure: {data}") from exc

    logger.debug("Generated comment for %r: %r", title[:60], comment)
    return comment
