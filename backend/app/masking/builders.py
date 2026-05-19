from presidio_analyzer import RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from .config import ENTITY_CONFIG


def build_anonymized(
    text: str,
    results: list[RecognizerResult],
    anonymizer: AnonymizerEngine,
) -> str:
    """Replace every detected PII span with its configured label.

    Example: "Max Mustermann" → "[PERSON]"
    """
    operators = {
        entity: OperatorConfig("replace", {"new_value": cfg.label})
        for entity, cfg in ENTITY_CONFIG.items()
    }
    return anonymizer.anonymize(
        text=text,
        analyzer_results=results,
        operators=operators,
    ).text


def build_preview(text: str, results: list[RecognizerResult]) -> str:
    """Wrap every detected PII span with an emoji color highlight.

    Example: "Max Mustermann" → "🟥`Max Mustermann`🟥"

    Results are applied in reverse order so that earlier character
    positions are not invalidated by insertions at later positions.
    """
    chars = list(text)
    for r in sorted(results, key=lambda r: r.start, reverse=True):
        cfg = ENTITY_CONFIG.get(r.entity_type)
        icon = cfg.color if cfg else "🔶"
        original = text[r.start : r.end]
        chars[r.start : r.end] = list(f"{icon}`{original}`{icon}")
    return "".join(chars)


def build_entities_found(
    text: str,
    results: list[RecognizerResult],
) -> list[dict]:
    """Build the metadata list of every entity that was detected.

    Returns one dict per result, sorted by position in the text,
    containing entity type, character offsets, confidence score,
    and the original text that was matched.
    """
    return [
        {
            "entity_type": r.entity_type,
            "start": r.start,
            "end": r.end,
            "score": round(r.score, 2),
            "original": text[r.start : r.end],
        }
        for r in sorted(results, key=lambda r: r.start)
    ]