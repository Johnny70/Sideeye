# ============================================================
# MODULE: tests/test_content_filter
# RESPONSIBILITY: Unit tests for content_filter module.
# DEPENDS ON: content_filter
# ============================================================

import pytest

from content_filter import apply_filter, is_filtered


# ── is_filtered ──────────────────────────────────────────────────────────────

def test_is_filtered_returns_true_for_blacklisted_title():
    article = {"title": "Mass shooting leaves dozens dead", "summary": ""}
    assert is_filtered(article) is True


def test_is_filtered_returns_true_for_blacklisted_summary():
    article = {"title": "Breaking news", "summary": "Earthquake kills hundreds"}
    assert is_filtered(article) is True


def test_is_filtered_returns_false_for_clean_article():
    article = {"title": "Tech company launches new product", "summary": "Revenue up 10 percent."}
    assert is_filtered(article) is False


def test_is_filtered_is_case_insensitive():
    article = {"title": "BOMBING campaign intensifies", "summary": ""}
    assert is_filtered(article) is True


def test_is_filtered_matches_word_boundary_only():
    # "attack" is blacklisted; must match exact word, not as substring of other words
    article_match = {"title": "Cyber attack on infrastructure", "summary": ""}
    article_no_match = {"title": "Proactive system update released", "summary": ""}
    assert is_filtered(article_match) is True
    assert is_filtered(article_no_match) is False


def test_is_filtered_handles_missing_keys_gracefully():
    # Article dict without title or summary should not raise
    article = {}
    result = is_filtered(article)
    assert isinstance(result, bool)


# ── apply_filter ─────────────────────────────────────────────────────────────

def test_apply_filter_removes_blacklisted_articles():
    articles = [
        {"title": "War breaks out in region", "summary": ""},
        {"title": "Scientists discover new species", "summary": ""},
    ]
    kept, removed = apply_filter(articles)
    assert len(kept) == 1
    assert removed == 1
    assert kept[0]["title"] == "Scientists discover new species"


def test_apply_filter_keeps_all_clean_articles():
    articles = [
        {"title": "Economy grows 3 percent", "summary": ""},
        {"title": "New programming language released", "summary": ""},
    ]
    kept, removed = apply_filter(articles)
    assert len(kept) == 2
    assert removed == 0


def test_apply_filter_removes_all_when_all_blacklisted():
    articles = [
        {"title": "Deadly flood kills 50", "summary": ""},
        {"title": "Shooting at school", "summary": "Terror group claims responsibility"},
    ]
    kept, removed = apply_filter(articles)
    assert len(kept) == 0
    assert removed == 2


def test_apply_filter_returns_correct_types():
    kept, removed = apply_filter([])
    assert isinstance(kept, list)
    assert isinstance(removed, int)
