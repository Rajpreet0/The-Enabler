import os
import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Context Rules — keyword-based context filter whitelist
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ContextRule:
    """Declares the context requirements for one entity type.

    Attributes:
        keywords:     Keywords that must appear near the match to keep it.
        window:       Character radius searched on each side of the match.
        nearest_wins: When True, a keyword is only credited to the closest
                      candidate of this entity type — the same nearest-wins
                      logic used for BIRTHDAY.  Use this for entities whose
                      regex is ambiguous (dates, short numbers) so that one
                      label doesn't accidentally validate multiple hits.
    """
    keywords:     frozenset[str]
    window:       int
    nearest_wins: bool = False


CONTEXT_RULES: dict[str, ContextRule] = {
    "BIRTHDAY": ContextRule(
        keywords=frozenset({
            "geboren", "geb.", "geburtsdatum", "geburtstag",
            "birthdate", "dob", "geb am",
        }),
        window=60,
        nearest_wins=True,
    ),
    "BANK_ACCOUNT_NUMBER": ContextRule(
        keywords=frozenset({
            "konto", "kontonummer", "konto-nr", "kto.", "kto-nr",
            "girokonto", "bankverbindung", "bank account",
        }),
        window=80,
    ),
    "TAX_CODE": ContextRule(
        keywords=frozenset({
            "steuer-id", "steuer id", "steueridentifikationsnummer",
            "steueridentifikation", "steuer-identifikationsnummer",
            "steuernummer", "steuer-nr", "steuer nr", "st.-nr", "st-nr",
            "tax id", "tax number",
        }),
        window=80,
    ),
    "LICENSE_PLATE_NUMBER": ContextRule(
        keywords=frozenset({
            "kennzeichen", "kfz-kennzeichen", "kfz kennzeichen",
            "fahrzeugkennzeichen", "amtliches kennzeichen",
            "license plate", "numberplate",
        }),
        window=80,
    ),
    "ID_CARD_NUMBER": ContextRule(
        keywords=frozenset({
            "personalausweis", "ausweis", "ausweis-nr", "ausweis nr",
            "ausweisnummer", "pass-nr", "reisepass", "passport",
            "identity card", "id card", "id-card", "id-nr",
        }),
        window=80,
    ),
}


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


# Priority ladder (higher = wins overlap resolution):
#   6  IBAN_CODE, TAX_CODE, ID_CARD_NUMBER   — structurally unique, never wrong
#   5  PERSON, ADDRESS                        — high-value PII, regex+NLP
#   4  EMAIL_ADDRESS, PHONE_NUMBER, URL,
#      BANK_ACCOUNT_NUMBER, LICENSE_PLATE_NUMBER, BIRTHDAY
#   3  LOCATION                               — NLP only, often inside addresses
#   2  ORGANIZATION                           — highest false-positive rate;
#                                               loses to every specific entity
ENTITY_CONFIG: dict[str, EntityConfig] = {
    "PERSON":               EntityConfig("[PERSON]",     "🟥", _threshold("THRESHOLD_PERSON",               0.80), 5),
    "EMAIL_ADDRESS":        EntityConfig("[EMAIL]",      "🟦", _threshold("THRESHOLD_EMAIL_ADDRESS",         0.50), 4),
    "PHONE_NUMBER":         EntityConfig("[TELEFON]",    "🟨", _threshold("THRESHOLD_PHONE_NUMBER",          0.50), 4),
    "URL":                  EntityConfig("[WEBSEITE]",   "🩵", _threshold("THRESHOLD_URL",                   0.50), 4),
    "LOCATION":             EntityConfig("[ORT]",        "🟩", _threshold("THRESHOLD_LOCATION",              0.85), 3),
    "IBAN_CODE":            EntityConfig("[IBAN]",       "🟪", _threshold("THRESHOLD_IBAN_CODE",             0.50), 6),
    "ORGANIZATION":         EntityConfig("[FIRMA]",      "🟧", _threshold("THRESHOLD_ORGANIZATION",          0.75), 2),
    "ADDRESS":              EntityConfig("[ADRESSE]",    "🟫", _threshold("THRESHOLD_ADDRESS",               0.55), 5),
    "TAX_CODE":             EntityConfig("[STEUER_ID]",  "🔴", _threshold("THRESHOLD_TAX_CODE",              0.85), 6),
    "BANK_ACCOUNT_NUMBER":  EntityConfig("[KONTO_NR]",   "🔵", _threshold("THRESHOLD_BANK_ACCOUNT_NUMBER",   0.80), 4),
    "LICENSE_PLATE_NUMBER": EntityConfig("[KFZ]",        "🟡", _threshold("THRESHOLD_LICENSE_PLATE_NUMBER",  0.90), 4),
    "BIRTHDAY":             EntityConfig("[GEBURTSTAG]", "🟠", _threshold("THRESHOLD_BIRTHDAY",              0.85), 4),
    "ID_CARD_NUMBER":       EntityConfig("[AUSWEIS_NR]", "🟣", _threshold("THRESHOLD_ID_CARD_NUMBER",        0.90), 6),
}


# Derived — do not edit directly, edit ENTITY_CONFIG above
ENTITIES: list[str] = list(ENTITY_CONFIG.keys())

# ---------------------------------------------------------------------------
# Static word / pattern constants
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Person salutation whitelist
# ---------------------------------------------------------------------------

# If one of these tokens appears directly before a PERSON span (within
# SALUTATION_WINDOW chars), the two-word minimum is relaxed so that
# single-word names like "Frau Müller" are still captured.
# This is intentionally non-blocking: if no salutation is present the
# normal two-word rule still applies.
SALUTATION_WINDOW = 30

SALUTATION_WORDS: frozenset[str] = frozenset({
    # German formal
    "herr", "frau", "herrn",
    # Academic / professional titles
    "dr.", "dr", "prof.", "prof", "dipl.", "ing.", "mag.", "doz.",
    "dr.-ing.", "prof.dr.", "prof.dr",
    # English
    "mr.", "mr", "mrs.", "mrs", "ms.", "ms", "miss", "sir", "madam",
    # Informal / digital
    "hr.", "hr", "fr.", "fr",
})


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

# German Tax ID (Steueridentifikationsnummer)
# 11 digits; first digit must not be 0. Separators (space or hyphen) optional.
# Formats: 12345678901 | 12 345 678 901 | 12-345-678-901
TAX_ID_RE = re.compile(r"\b(?!0)\d{2}[ -]?\d{3}[ -]?\d{3}[ -]?\d{3}\b")

# German bank account number (Kontonummer)
# 8–10 digit sequence, typically embedded in an IBAN — match only with word boundaries.
BANK_ACC_NUMBER_RE = re.compile(r"\b\d{8,10}\b")

# German vehicle license plate (Kfz-Kennzeichen)
# Format: <district 1-3 letters> - <ID 1-2 letters> <number 1-4 digits> [E|H]
# Umlauts supported in district code (e.g. GÖ, OÄ).
# Optional E (Elektro) or H (Historisch) suffix.
LICENSE_PLATE_NUMBER_RE = re.compile(r"\b[A-ZÄÖÜ]{1,3}-[A-Z]{1,2}[ -]?\d{1,4}[EH]?\b")

# German date of birth
# Supports DD.MM.YYYY, DD/MM/YYYY, DD.MM.YY, DD/MM/YY
BIRTHDAY_RE = re.compile(r"\b(0[1-9]|[12]\d|3[01])[./](0[1-9]|1[012])[./](\d{4}|\d{2})\b")

# German phone numbers
# Covers: +49 69 555 382-99 | +49 (0)69 555 382-0 | 0049 69 ... | 069 555382
# Deliberately requires either a country code (+49/0049) or a leading zero (local area code)
# to avoid matching arbitrary digit sequences.
PHONE_RE = re.compile(
    r"(?:"
    r"\+49[\s\-\.]?\(?0?\)?[\s\-\.]?"   # +49 or +49 (0)
    r"|0049[\s\-\.]?\(?0?\)?[\s\-\.]?"  # 0049 or 0049 (0)
    r"|0\d{2,5}[\s\-\/\.]"              # local area code starting with 0
    r")"
    r"[\d][\d\s\-\/\.]{4,14}\d",        # subscriber number, allow separators mid-number
    re.ASCII,
)

# German ID card number (Personalausweis, format since 2010)
# 10 characters: 9 alphanumeric (subset) + 1 numeric check digit.
ID_CARD_NUMBER_RE = re.compile(r"\b[C-FGHJKLMNPRSTV-XYZ0-9]{9}\d\b")

# URL validation — must look like a real web address, not a file reference.
# Requires either a scheme (http/https/ftp) OR a www. prefix OR a known TLD at the end.
URL_VALID_RE = re.compile(
    r"(?:"
    r"https?://[^\s]+"                         # http(s):// anything
    r"|ftp://[^\s]+"                           # ftp:// anything
    r"|www\.[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}"     # www.example.de
    r"|[a-zA-Z0-9\-]+\."
    r"(?:de|com|org|net|at|ch|eu|io|gov|edu|info|biz|co|uk|fr|nl|it|es|pl|ru|cn|jp|br|au)"
    r"(?:[/\?#][^\s]*)?"                       # optional path/query
    r")",
    re.IGNORECASE,
)

# File extensions that are never URLs
URL_BLACKLIST_EXTENSIONS = frozenset({
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".tiff", ".ico",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".mp3", ".mp4", ".avi", ".mov", ".mkv",
    ".exe", ".dll", ".so", ".bin",
    ".css", ".js", ".ts", ".json", ".xml", ".csv",
})
