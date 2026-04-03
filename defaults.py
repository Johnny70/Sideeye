# ============================================================
# MODULE: defaults
# RESPONSIBILITY: Default configuration values and first-run file initialisation.
# DEPENDS ON: config, json, logging, pathlib (stdlib)
# EXPOSES: DEFAULT_FEEDS, DEFAULT_INTERESTS, DEFAULT_SETTINGS, init_file_if_missing
# ============================================================

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_FEEDS = {
    "feeds": [
        {"name": "BBC World News",     "url": "https://feeds.bbci.co.uk/news/world/rss.xml",  "category": "world"},
        {"name": "Al Jazeera English", "url": "https://www.aljazeera.com/xml/rss/all.xml",     "category": "world"},
        {"name": "The Guardian World", "url": "https://www.theguardian.com/world/rss",         "category": "world"},
    ]
}

DEFAULT_INTERESTS = {
    "interests": [
        {"topic": "technology", "score": 8},
        {"topic": "science",    "score": 7},
        {"topic": "economy",    "score": 6},
        {"topic": "climate",    "score": 5},
        {"topic": "world",      "score": 4},
    ]
}

DEFAULT_SETTINGS = {
    "system_prompt": (
        "You are a dry-witted news commentator. "
        "Given a headline and summary, reply with a single sharp remark (1-2 sentences). "
        "Do not repeat the headline. No hashtags, no emojis, no quotation marks."
    ),
    "temperature": 0.8,
}


def init_file_if_missing(path: Path, default: dict) -> bool:
    """Write default JSON to path if the file does not exist. Returns True if created."""
    if not path.exists():
        with path.open("w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
        logger.info("Created default %s", path.name)
        return True
    return False
