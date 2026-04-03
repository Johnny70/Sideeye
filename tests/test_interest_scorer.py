# ============================================================
# MODULE: tests/test_interest_scorer
# RESPONSIBILITY: Unit tests for interest_scorer module.
# DEPENDS ON: interest_scorer
# ============================================================

import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from interest_scorer import _keywords, load_interests, score_articles


# ── _keywords ────────────────────────────────────────────────────────────────

def test_keywords_extracts_significant_words():
    result = _keywords("Artificial Intelligence")
    assert "Artificial" in result or "artificial" in result.copy()
    # Both words are significant; neither is a stopword
    assert len(result) == 2


def test_keywords_removes_stopwords():
    result = _keywords("The future of AI")
    # "The" and "of" are stopwords
    words_lower = [w.lower() for w in result]
    assert "the" not in words_lower
    assert "of" not in words_lower
    assert "future" in words_lower
    assert "ai" in words_lower


def test_keywords_returns_empty_for_only_stopwords():
    result = _keywords("the and or")
    assert result == []


def test_keywords_handles_hyphenated_and_numeric():
    result = _keywords("COVID-19 pandemic")
    words_lower = [w.lower() for w in result]
    assert "covid" in words_lower or "19" in words_lower


# ── load_interests ───────────────────────────────────────────────────────────

def test_load_interests_returns_empty_list_when_file_missing():
    with patch("interest_scorer.INTERESTS_FILE", Path("/nonexistent/path/interests.json")):
        result = load_interests()
    assert result == []


def test_load_interests_returns_empty_list_on_invalid_json(tmp_path):
    bad_json = tmp_path / "interests.json"
    bad_json.write_text("not valid json", encoding="utf-8")
    with patch("interest_scorer.INTERESTS_FILE", bad_json):
        result = load_interests()
    assert result == []


def test_load_interests_returns_empty_list_when_key_missing(tmp_path):
    missing_key = tmp_path / "interests.json"
    missing_key.write_text(json.dumps({"wrong_key": []}), encoding="utf-8")
    with patch("interest_scorer.INTERESTS_FILE", missing_key):
        result = load_interests()
    assert result == []


def test_load_interests_returns_list_from_valid_file(tmp_path):
    valid = tmp_path / "interests.json"
    valid.write_text(json.dumps({"interests": [{"topic": "AI", "score": 9}]}), encoding="utf-8")
    with patch("interest_scorer.INTERESTS_FILE", valid):
        result = load_interests()
    assert len(result) == 1
    assert result[0]["topic"] == "AI"


# ── score_articles ───────────────────────────────────────────────────────────

_FAKE_INTERESTS = [
    {"topic": "Artificial Intelligence", "score": 10},
    {"topic": "Space Exploration", "score": 8},
    {"topic": "Economics", "score": 3},
]

_ARTICLES = [
    {"title": "New AI model breaks records", "summary": "Artificial intelligence progress."},
    {"title": "NASA plans Moon mission", "summary": "Space exploration milestone."},
    {"title": "Stock market update", "summary": "Economics report"},
]


def test_score_articles_adds_score_field():
    with patch("interest_scorer.load_interests", return_value=_FAKE_INTERESTS):
        scored = score_articles(_ARTICLES)
    assert all("score" in a for a in scored)


def test_score_articles_sorts_by_score_descending():
    with patch("interest_scorer.load_interests", return_value=_FAKE_INTERESTS):
        scored = score_articles(_ARTICLES)
    scores = [a["score"] for a in scored]
    assert scores == sorted(scores, reverse=True)


def test_score_articles_returns_all_articles():
    with patch("interest_scorer.load_interests", return_value=_FAKE_INTERESTS):
        scored = score_articles(_ARTICLES)
    assert len(scored) == len(_ARTICLES)


def test_score_articles_returns_zero_score_when_no_interests():
    with patch("interest_scorer.load_interests", return_value=[]):
        scored = score_articles([{"title": "Test article", "summary": "Content here"}])
    assert scored[0]["score"] == 0
