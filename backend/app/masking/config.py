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
 
 
ENTITY_CONFIG: dict[str, EntityConfig] = {
    "PERSON":        EntityConfig("[PERSON]",  "🟥", 0.7,  3),
    "EMAIL_ADDRESS": EntityConfig("[EMAIL]",   "🟦", 0.5,  4),
    "PHONE_NUMBER":  EntityConfig("[TELEFON]", "🟨", 0.5,  4),
    "LOCATION":      EntityConfig("[ORT]",     "🟩", 0.7,  2),
    "IBAN_CODE":     EntityConfig("[IBAN]",    "🟪", 0.5,  4),
    "ORGANIZATION":  EntityConfig("[FIRMA]",   "🟧", 0.75, 4),
    "ADDRESS":       EntityConfig("[ADRESSE]", "🟫", 0.55, 5),
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