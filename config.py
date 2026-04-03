# ============================================================
# MODULE: config
# RESPONSIBILITY: Shared file-path constants and polling interval.
# DEPENDS ON: pathlib (stdlib)
# EXPOSES: FEEDS_FILE, INTERESTS_FILE, SETTINGS_FILE, STATIC_DIR, POLL_INTERVAL
# ============================================================

from pathlib import Path

FEEDS_FILE     = Path(__file__).parent / "feeds.json"
INTERESTS_FILE = Path(__file__).parent / "interests.json"
SETTINGS_FILE  = Path(__file__).parent / "settings.json"
STATIC_DIR     = Path(__file__).parent / "static"
POLL_INTERVAL  = 300  # sekunder
