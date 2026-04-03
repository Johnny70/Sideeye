# ============================================================
# MODULE: content_filter
# RESPONSIBILITY: Filter articles that match blacklisted negative-content keywords.
# DEPENDS ON: re (stdlib)
# EXPOSES: is_filtered, apply_filter
# ============================================================

import logging
import re

logger = logging.getLogger(__name__)

# ── Nyckelord per kategori ───────────────────────────────────────────────────
_KEYWORDS: list[str] = [
    # Krig & väpnade konflikter
    "war", "warfare", "airstrike", "air strike", "bombing", "bombed", "missile",
    "troops", "invasion", "invade", "military offensive", "shelling", "ceasefire",
    "combat", "casualties", "battlefield", "siege", "warzone", "insurgent",
    "militant", "guerrilla", "armed conflict", "nato strike", "drone strike",

    # Dödsfall
    "killed", "dead", "death", "deaths", "died", "fatalities", "fatal",
    "found dead", "body found", "remains found", "murder", "murdered",
    "homicide", "execution", "executed",

    # Naturkatastrofer
    "earthquake", "tsunami", "hurricane", "tornado", "cyclone", "typhoon",
    "wildfire", "flood", "flooding", "landslide", "avalanche", "volcano",
    "eruption", "drought", "disaster",

    # Självmord
    "suicide", "suicidal", "took his own life", "took her own life",
    "self-harm", "self harm",

    # Våld & brott
    "assault", "attacked", "stabbed", "stabbing", "shooting", "shot",
    "gunshot", "gunfire", "beaten", "battered", "violence", "violent",
    "brutally", "slain", "slaughter", "massacre", "genocide", "ethnic cleansing",

    # Sjukdomsutbrott
    "outbreak", "epidemic", "pandemic", "infection surge", "death toll",
    "ebola", "cholera", "plague", "mpox", "monkeypox",

    # Etniska & religiösa konflikter
    "sectarian", "ethnic tension", "religious violence", "persecution",
    "discrimination", "hate crime", "pogrom",

    # Politiskt förtryck
    "crackdown", "repression", "oppression", "detained", "arrested dissidents",
    "political prisoner", "torture", "forced disappearance",

    # Flyktingkriser
    "refugee", "refugees", "migrant crisis", "displaced", "asylum seekers",
    "deportation", "expulsion", "boat people", "border crossing deaths",

    # Terror & masskjutningar
    "terror", "terrorist", "terrorism", "attack", "mass shooting",
    "mass casualty", "bomb blast", "explosion", "hostage", "hijack",
    "car bomb", "suicide bomb",

    # Kidnappningar & övergrepp
    "kidnap", "kidnapped", "abducted", "abduction", "trafficking",
    "human trafficking", "sexual assault", "rape", "abuse", "child abuse",
    "grooming", "exploitation",

    # Barn i utsatta situationer
    "child soldier", "child soldiers", "child casualties", "children killed",
    "children dead", "orphan", "missing child", "missing children",
    "child labor", "child labour", "trafficking children",
]

# Kompilera till ett enda regex för effektivitet
_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(kw) for kw in _KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def is_filtered(article: dict) -> bool:
    """Returnerar True om artikeln bör filtreras bort."""
    text = " ".join([
        article.get("title", ""),
        article.get("summary", ""),
    ])
    return bool(_PATTERN.search(text))


def apply_filter(articles: list[dict]) -> tuple[list[dict], int]:
    """
    Filtrerar en lista artiklar.
    Returnerar (godkända artiklar, antal bortfiltrerade).
    """
    kept = [a for a in articles if not is_filtered(a)]
    removed = len(articles) - len(kept)
    return kept, removed
