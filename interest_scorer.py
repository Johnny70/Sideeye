# ============================================================
# MODULE: interest_scorer
# RESPONSIBILITY: Score and rank articles by relevance against user-defined interest topics.
# DEPENDS ON: re, json, pathlib (stdlib)
# EXPOSES: load_interests, score_articles
# ============================================================

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

INTERESTS_FILE = Path(__file__).parent / "interests.json"

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "has", "have", "had", "not", "no", "can", "will", "would", "could",
    "should", "this", "that", "these", "those", "it", "its", "so", "if",
    "as", "do", "does", "did", "up", "out", "about", "over", "under",
}


def _keywords(topic: str) -> list[str]:
    """Extraherar signifikanta ord ur ett ämnesnamn."""
    words = re.findall(r"[A-Za-z0-9]+", topic)
    return [w for w in words if w.lower() not in _STOPWORDS and len(w) >= 2]


def load_interests() -> list[dict]:
    try:
        with INTERESTS_FILE.open(encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error("interests.json not found at %s", INTERESTS_FILE)
        return []
    except json.JSONDecodeError as exc:
        logger.error("interests.json is not valid JSON: %s", exc)
        return []
    if "interests" not in data:
        logger.error("interests.json is missing top-level 'interests' key")
        return []
    return data["interests"]


def score_articles(articles: list[dict]) -> list[dict]:
    """
    Scores and sorts articles by total interest score.
    Each article gets a 'score' field (sum of matched interest scores).
    """
    interests = load_interests()

    # Pre-compile one pattern per interest
    matchers: list[tuple[re.Pattern, int]] = []
    for item in interests:
        kws = _keywords(item["topic"])
        if not kws:
            continue
        pat = re.compile(
            r"\b(" + "|".join(re.escape(k) for k in kws) + r")\b",
            re.IGNORECASE,
        )
        matchers.append((pat, int(item.get("score", 0))))

    scored: list[dict] = []
    for article in articles:
        text = f"{article.get('title', '')} {article.get('summary', '')}"
        total = sum(s for pat, s in matchers if pat.search(text))
        scored.append({**article, "score": total})

    scored.sort(key=lambda a: a["score"], reverse=True)
    return scored
