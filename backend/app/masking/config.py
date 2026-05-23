import os
import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Entity Configuration — single source of truth for all entity-level settings
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class EntityConfig:
    label: str        # Replacement label in anonymized text e.g. "[PERSON]"
    color: str        # Emoji color used in the preview highlight
    min_score: float  # Minimum confidence score to accept a hit
    priority: int     # Overlap resolution priority (higher = wins)


def _threshold(env_key: str, default: float) -> float:
    """Return threshold from env var (e.g. THRESHOLD_PERSON=0.85) or default."""
    raw = os.environ.get(env_key)
    if raw is not None:
        try:
            return float(raw)
        except ValueError:
            pass
    return default


ENTITY_CONFIG: dict[str, EntityConfig] = {
    "PERSON":        EntityConfig("[PERSON]",  "🟥", _threshold("THRESHOLD_PERSON",       0.80), 3),
    "EMAIL_ADDRESS": EntityConfig("[EMAIL]",   "🟦", _threshold("THRESHOLD_EMAIL_ADDRESS", 0.50), 4),
    "PHONE_NUMBER":  EntityConfig("[TELEFON]", "🟨", _threshold("THRESHOLD_PHONE_NUMBER",  0.50), 4),
    "LOCATION":      EntityConfig("[ORT]",     "🟩", _threshold("THRESHOLD_LOCATION",      0.75), 2),
    "IBAN_CODE":     EntityConfig("[IBAN]",    "🟪", _threshold("THRESHOLD_IBAN_CODE",     0.50), 4),
    "ORGANIZATION":  EntityConfig("[FIRMA]",   "🟧", _threshold("THRESHOLD_ORGANIZATION",  0.70), 4),
    "ADDRESS":       EntityConfig("[ADRESSE]", "🟫", _threshold("THRESHOLD_ADDRESS",       0.55), 5),
}
 

# Derived — do not edit directly, edit ENTITY_CONFIG above
ENTITIES: list[str] = list(ENTITY_CONFIG.keys())
 
# ---------------------------------------------------------------------------
# Static word / pattern constants
# ---------------------------------------------------------------------------
 
# Words that must never be flagged as PERSON / LOCATION / ORGANIZATION
FALSE_POSITIVE_WORDS: set[str] = {
    "diese", "dieser", "dieses", "hinweise", "hinweis", "datum", "betreff",
    "prüfcode", "pruefcode", "matrikelnummer", "semesterzeitraum", "beurlaubt",
    "nachname", "vorname", "geburtsdatum", "fachsemester", "studienfach",
    "abschluss", "bescheinigung", "unterschrift", "stempel", "webseite",
    "verifikation", "nutzung", "genannte", "person", "dezernat", "referat",
    "studium", "lehre", "hochschulrecht", "studierendenangelegenheiten",
    "präsidentin", "präsident", "wintersommer", "wintersemester",
    "sommersemester", "informatik", "semester",
}
 
STREET_KEYWORDS = re.compile(
    r"(?:Straße|Strasse|straße|strasse|Str\b|Weg\b|Allee\b|Gasse\b|Platz\b|Ring\b|Damm\b|Chaussee\b)",
    re.IGNORECASE,
)
 
ADDRESS_RE = re.compile(
    r"\b[A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ\-]{1,30}"
    r"(?:straße|strasse|Straße|Strasse|str\.|Str\.|weg|Weg|allee|Allee|gasse|Gasse|platz|Platz|ring|Ring|damm|Damm)"
    r"\.?\s+\d{1,4}[a-z]?"
    r"(?:\s+\d{5}\s+[A-ZÄÖÜ][a-zäöüß\-]+)?",
)
 
PLZ_RE = re.compile(r"\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß\-]+\b")