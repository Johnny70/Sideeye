# ============================================================
# MODULE: tests/test_llm_client
# RESPONSIBILITY: Unit tests for llm_client module.
# DEPENDS ON: llm_client
# ============================================================

import json
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_client import _api_key, _load_settings, generate_comment


# ── _api_key ─────────────────────────────────────────────────────────────────

def test_api_key_raises_when_not_set():
    with patch.dict("os.environ", {}, clear=True):
        # Remove the key if set
        import os
        os.environ.pop("DEEPINFRA_API_KEY", None)
        with pytest.raises(RuntimeError, match="DEEPINFRA_API_KEY"):
            _api_key()


def test_api_key_returns_value_when_set():
    with patch.dict("os.environ", {"DEEPINFRA_API_KEY": "test-key-123"}):
        assert _api_key() == "test-key-123"


# ── _load_settings ───────────────────────────────────────────────────────────

def test_load_settings_returns_defaults_when_file_missing():
    with patch("llm_client._SETTINGS_FILE", Path("/nonexistent/settings.json")):
        prompt, temperature = _load_settings()
    assert isinstance(prompt, str)
    assert len(prompt) > 0
    assert isinstance(temperature, float)


def test_load_settings_returns_values_from_file(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"system_prompt": "Be funny.", "temperature": 1.2}), encoding="utf-8")
    with patch("llm_client._SETTINGS_FILE", settings):
        prompt, temperature = _load_settings()
    assert prompt == "Be funny."
    assert temperature == 1.2


def test_load_settings_falls_back_on_invalid_json(tmp_path):
    bad = tmp_path / "settings.json"
    bad.write_text("not json", encoding="utf-8")
    with patch("llm_client._SETTINGS_FILE", bad):
        prompt, temperature = _load_settings()
    assert isinstance(prompt, str)
    assert isinstance(temperature, float)


# ── generate_comment ─────────────────────────────────────────────────────────

_FAKE_RESPONSE = {
    "choices": [{"message": {"content": "What a time to be alive."}}]
}


def test_generate_comment_returns_comment():
    mock_response = MagicMock()
    mock_response.json.return_value = _FAKE_RESPONSE
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("llm_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"DEEPINFRA_API_KEY": "test-key"}):
        result = asyncio.run(generate_comment("Test headline", "Test summary"))

    assert result == "What a time to be alive."


def test_generate_comment_raises_on_http_error():
    import httpx

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=httpx.HTTPError("connection failed"))

    with patch("llm_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"DEEPINFRA_API_KEY": "test-key"}):
        with pytest.raises(RuntimeError, match="DeepInfra API request failed"):
            asyncio.run(generate_comment("Test headline", ""))


def test_generate_comment_raises_on_unexpected_response_structure():
    mock_response = MagicMock()
    mock_response.json.return_value = {"unexpected": "structure"}
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("llm_client.httpx.AsyncClient", return_value=mock_client), \
         patch.dict("os.environ", {"DEEPINFRA_API_KEY": "test-key"}):
        with pytest.raises(RuntimeError, match="Unexpected API response"):
            asyncio.run(generate_comment("Test headline", ""))
