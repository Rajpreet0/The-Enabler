import re
from dataclasses import dataclass
from functools import lru_cache

from presidio_analyzer import (
    AnalyzerEngine,
    RecognizerResult,
    PatternRecognizer,
    Pattern,
)
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "LOCATION",
    "IBAN_CODE",
    "ORGANIZATION",
    "ADDRESS",
]

HIGHLIGHT_COLORS: dict[str, str] = {
    "PERSON": "🟥",
    "EMAIL_ADDRESS": "🟦",
    "PHONE_NUMBER": "🟨",
    "LOCATION": "🟩",
    "IBAN_CODE": "🟪",
    "ORGANIZATION": "🟧",
    "ADDRESS": "🟫",
}

ANONYMIZE_LABELS: dict[str, str] = {
    "PERSON": "[PERSON]",
    "EMAIL_ADDRESS": "[EMAIL]",
    "PHONE_NUMBER": "[TELEFON]",
    "LOCATION": "[ORT]",
    "IBAN_CODE": "[IBAN]",
    "ORGANIZATION": "[FIRMA]",
    "ADDRESS": "[ADRESSE]",
}

# Mindest-Score damit ein Treffer akzeptiert wird
_MIN_SCORE: dict[str, float] = {
    "PERSON": 0.7,
    "LOCATION": 0.7,
    "ORGANIZATION": 0.75,
    "EMAIL_ADDRESS": 0.5,
    "PHONE_NUMBER": 0.5,
    "IBAN_CODE": 0.5,
    "ADDRESS": 0.55,
}

# Wörter die NIEMALS als PERSON/LOCATION/ORGANIZATION durchgehen
_FALSE_POSITIVE_WORDS = {
    # Deutsche Dokument-Begriffe
    "diese",
    "dieser",
    "dieses",
    "hinweise",
    "hinweis",
    "datum",
    "betreff",
    "prüfcode",
    "pruefcode",
    "matrikelnummer",
    "semesterzeitraum",
    "beurlaubt",
    "nachname",
    "vorname",
    "geburtsdatum",
    "fachsemester",
    "studienfach",
    "abschluss",
    "bescheinigung",
    "unterschrift",
    "stempel",
    "webseite",
    "verifikation",
    "nutzung",
    "genannte",
    "person",
    "dezernat",
    "referat",
    "studium",
    "lehre",
    "hochschulrecht",
    "studierendenangelegenheiten",
    "präsidentin",
    "präsident",
    "wintersommer",
    "wintersemester",
    "sommersemester",
    "informatik",
    "semester",
}

# Straßen-Keywords
_STREET_KEYWORDS = re.compile(
    r"(?:Straße|Strasse|straße|strasse|Str\b|Weg\b|Allee\b|Gasse\b|Platz\b|Ring\b|Damm\b|Chaussee\b)",
    re.IGNORECASE,
)

# Vollständige deutsche Adresse
_ADDRESS_RE = re.compile(
    r"\b[A-ZÄÖÜ][a-zäöüßA-ZÄÖÜ\-]{1,30}"
    r"(?:straße|strasse|Straße|Strasse|str\.|Str\.|weg|Weg|allee|Allee|gasse|Gasse|platz|Platz|ring|Ring|damm|Damm)"
    r"\.?\s+\d{1,4}[a-z]?"
    r"(?:\s+\d{5}\s+[A-ZÄÖÜ][a-zäöüß\-]+)?",
)

# Nur PLZ + Ort (5-stellig gefolgt von einem Wort mit Großbuchstaben)
_PLZ_RE = re.compile(r"\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß\-]+\b")


def _build_address_recognizer() -> PatternRecognizer:
    return PatternRecognizer(
        supported_entity="ADDRESS",
        patterns=[
            Pattern(name="de_full_address", regex=_ADDRESS_RE.pattern, score=0.85),
            Pattern(name="de_plz_ort", regex=_PLZ_RE.pattern, score=0.6),
        ],
        supported_language="de",
    )


def _build_org_recognizer() -> PatternRecognizer:
    # Nur Firmen mit explizitem Rechtsform-Suffix erkennen
    return PatternRecognizer(
        supported_entity="ORGANIZATION",
        patterns=[
            Pattern(
                name="de_org_suffix",
                regex=r"\b[A-ZÄÖÜ][A-Za-zäöüÄÖÜß&\s\-\.]{2,50}"
                r"(?:GmbH|AG|KG|OHG|UG|e\.V\.|gGmbH|SE)(?:\s*&\s*Co\.?\s*KG)?\b",
                score=0.88,
            ),
        ],
        supported_language="de",
    )


@lru_cache(maxsize=1)
def _get_engines() -> tuple[AnalyzerEngine, AnonymizerEngine]:
    nlp_config = {
        "nlp_engine_name": "spacy",
        "models": [
            {"lang_code": "en", "model_name": "en_core_web_lg"},
            {"lang_code": "de", "model_name": "de_core_news_lg"},
        ],
    }
    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_config).create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en", "de"])
    analyzer.registry.add_recognizer(_build_address_recognizer())
    analyzer.registry.add_recognizer(_build_org_recognizer())
    anonymizer = AnonymizerEngine()
    return analyzer, anonymizer


@dataclass
class MaskingResult:
    preview: str
    anonymized: str
    entities_found: list[dict]


def mask_text(text: str, language: str = "en") -> MaskingResult:
    analyzer, anonymizer = _get_engines()

    results: list[RecognizerResult] = analyzer.analyze(
        text=text,
        entities=ENTITIES,
        language=language,
    )

    # Schritt 1: Schwache Treffer und False Positives rausfiltern
    results = _filter_results(results, text)

    # Schritt 2: Adressen direkt per Regex finden
    regex_addresses = _find_addresses_in_text(text)

    # Schritt 3: PERSON-Spans die Straßen-Keywords enthalten kürzen
    #            Namen VOR dem Trimmen merken für Propagation
    known_names = _extract_person_names(results, text)
    results = _trim_person_spans(results, text)

    # Schritt 4: Name Propagation
    propagated = _propagate_persons(known_names, results, text)

    # Schritt 5: Alles zusammenführen + Überlappungen auflösen
    all_results = list(results) + regex_addresses + propagated
    all_results = _resolve_overlaps(all_results)

    entities_found = [
        {
            "entity_type": r.entity_type,
            "start": r.start,
            "end": r.end,
            "score": round(r.score, 2),
            "original": text[r.start : r.end],
        }
        for r in sorted(all_results, key=lambda r: r.start)
    ]

    operators = {
        entity: OperatorConfig("replace", {"new_value": label})
        for entity, label in ANONYMIZE_LABELS.items()
    }
    anonymized_result = anonymizer.anonymize(
        text=text,
        analyzer_results=all_results,
        operators=operators,
    )

    preview_chars = list(text)
    for r in sorted(all_results, key=lambda r: r.start, reverse=True):
        icon = HIGHLIGHT_COLORS.get(r.entity_type, "🔶")
        original = text[r.start : r.end]
        replacement = f"{icon}`{original}`{icon}"
        preview_chars[r.start : r.end] = list(replacement)

    return MaskingResult(
        preview="".join(preview_chars),
        anonymized=anonymized_result.text,
        entities_found=entities_found,
    )


def _filter_results(
    results: list[RecognizerResult], text: str
) -> list[RecognizerResult]:
    """Filtert False Positives und schwache Treffer."""
    kept = []
    for r in results:
        span = text[r.start : r.end].strip()

        # Score-Schwelle prüfen
        min_score = _MIN_SCORE.get(r.entity_type, 0.5)
        if r.score < min_score:
            continue

        # Bekannte False-Positive-Wörter rausfiltern (case-insensitive)
        if span.lower() in _FALSE_POSITIVE_WORDS:
            continue

        # PERSON muss mindestens 2 Wörter haben (Vor- + Nachname)
        if r.entity_type == "PERSON":
            words = span.split()
            if len(words) < 2:
                continue
            # Kein Wort darf rein aus Großbuchstaben bestehen (kein Header-Text)
            if any(w.isupper() and len(w) > 2 for w in words):
                continue

        # LOCATION: Einzel-Wörter aus der False-Positive-Liste schon gefiltert,
        # aber auch generische Begriffe wie "Diese", "Dezernat" etc. raus
        if r.entity_type == "LOCATION":
            if len(span) < 4:
                continue
            # Hex-artige Strings sind keine Orte (z.B. "fe5b0199")
            if re.fullmatch(r"[0-9a-fA-F]{6,}", span):
                continue

        kept.append(r)
    return kept


def _extract_person_names(results: list[RecognizerResult], text: str) -> set[str]:
    """Extrahiert Personennamen inkl. gekürzter Varianten (vor dem Trimmen)."""
    names = set()
    for r in results:
        if r.entity_type != "PERSON":
            continue
        span = text[r.start : r.end].strip()
        names.add(span)
        m = _STREET_KEYWORDS.search(span)
        if m:
            clean = span[: m.start()].strip()
            if clean:
                names.add(clean)
    return names


def _propagate_persons(
    known_names: set[str],
    results: list[RecognizerResult],
    text: str,
) -> list[RecognizerResult]:
    """Sucht alle bekannten Personennamen nochmal im gesamten Text."""
    existing_spans = {(r.start, r.end) for r in results}
    propagated = []
    for name in known_names:
        if not name or len(name.split()) < 2:
            continue
        for m in re.finditer(re.escape(name), text):
            span = (m.start(), m.end())
            if span not in existing_spans:
                propagated.append(RecognizerResult("PERSON", m.start(), m.end(), 0.80))
                existing_spans.add(span)
    return propagated


def _find_addresses_in_text(text: str) -> list[RecognizerResult]:
    """Findet Adressen direkt per Regex."""
    found = []
    for m in _ADDRESS_RE.finditer(text):
        found.append(RecognizerResult("ADDRESS", m.start(), m.end(), 0.85))
    address_spans = [(r.start, r.end) for r in found]
    for m in _PLZ_RE.finditer(text):
        covered = any(s <= m.start() and m.end() <= e for s, e in address_spans)
        if not covered:
            found.append(RecognizerResult("ADDRESS", m.start(), m.end(), 0.6))
    return found


def _trim_person_spans(
    results: list[RecognizerResult], text: str
) -> list[RecognizerResult]:
    """Kürzt PERSON-Spans die Straßen-Keywords enthalten."""
    trimmed = []
    for r in results:
        if r.entity_type == "PERSON":
            span = text[r.start : r.end]
            m = _STREET_KEYWORDS.search(span)
            if m:
                clean = span[: m.start()].strip()
                if clean and len(clean.split()) >= 2:
                    r = RecognizerResult(
                        "PERSON", r.start, r.start + len(clean), r.score
                    )
                else:
                    continue
        trimmed.append(r)
    return trimmed


_ENTITY_PRIORITY = {
    "ADDRESS": 5,
    "ORGANIZATION": 4,
    "IBAN_CODE": 4,
    "EMAIL_ADDRESS": 4,
    "PHONE_NUMBER": 4,
    "PERSON": 3,
    "LOCATION": 2,
}


def _resolve_overlaps(results: list[RecognizerResult]) -> list[RecognizerResult]:
    """Löst Überlappungen auf — höhere Priorität dann Score gewinnt."""

    def rank(r: RecognizerResult) -> tuple:
        return (_ENTITY_PRIORITY.get(r.entity_type, 1), r.score)

    sorted_results = sorted(
        results,
        key=lambda r: (r.start, -_ENTITY_PRIORITY.get(r.entity_type, 1), -r.score),
    )
    kept: list[RecognizerResult] = []
    for r in sorted_results:
        if not kept or r.start >= kept[-1].end:
            kept.append(r)
        elif rank(r) > rank(kept[-1]):
            kept[-1] = r
    return kept
