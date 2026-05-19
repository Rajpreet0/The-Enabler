"""masking — PII detection and anonymization package.

Public API
----------
mask_text(text, language, pipeline) -> MaskingResult
MaskingResult(preview, anonymized, entities_found)

Everything else (engines, steps, builders, config) is internal.
Import from the submodules directly only if you need to customise
the pipeline or extend it with your own steps.
"""

from dataclasses import dataclass

from .config import ENTITIES
from .engines import get_engines
from .pipeline import MaskingPipeline
from .steps import DEFAULT_PIPELINE
from .builders import build_anonymized, build_preview, build_entities_found


@dataclass
class MaskingResult:
    preview: str               # Original text with emoji-highlighted PII spans
    anonymized: str            # Text with PII replaced by labels like [PERSON]
    entities_found: list[dict] # Metadata: entity type, position, score, original text


def mask_text(
    text: str,
    language: str = "en",
    pipeline: MaskingPipeline = DEFAULT_PIPELINE,
) -> MaskingResult:
    """Detect and mask PII in *text* using the given *pipeline*.

    Args:
        text:     The raw input text to anonymize.
        language: ISO language code ('en' or 'de') for NLP entity recognition.
        pipeline: The MaskingPipeline to use. Defaults to DEFAULT_PIPELINE.
                  Pass a custom pipeline to swap, skip, or reorder steps.

    Returns:
        A MaskingResult with the anonymized text, a highlighted preview,
        and a list of every entity that was found.

    Example:
        result = mask_text("Hallo, ich bin Max Mustermann.", language="de")
        print(result.anonymized)   # "Hallo, ich bin [PERSON]."
        print(result.preview)      # "Hallo, ich bin 🟥`Max Mustermann`🟥."
    """
    analyzer, anonymizer = get_engines()

    raw_results = analyzer.analyze(
        text=text,
        entities=ENTITIES,
        language=language,
    )

    final_results = pipeline.run(raw_results, text)

    return MaskingResult(
        preview=build_preview(text, final_results),
        anonymized=build_anonymized(text, final_results, anonymizer),
        entities_found=build_entities_found(text, final_results),
    )


__all__ = ["mask_text", "MaskingResult"]