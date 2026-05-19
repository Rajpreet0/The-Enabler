import re

from presidio_analyzer import RecognizerResult

from .config import (
    ENTITY_CONFIG,
    FALSE_POSITIVE_WORDS,
    STREET_KEYWORDS,
    ADDRESS_RE,
    PLZ_RE,
)
from .pipeline import PipelineStep, MaskingPipeline


# ---------------------------------------------------------------------------
# Step 1 — Filter
# ---------------------------------------------------------------------------

class FilterStep(PipelineStep):
    """Removes low-confidence hits and known false positives.

    Checks:
    - Score is above the per-entity minimum threshold
    - Span text is not in the false-positive word list
    - PERSON entities have at least two words (first + last name)
    - PERSON entities contain no all-caps words (e.g. document headers)
    - LOCATION entities are at least 4 characters and not hex strings
    """

    def run(self, results: list[RecognizerResult], text: str) -> list[RecognizerResult]:
        kept = []
        for r in results:
            span = text[r.start : r.end].strip()
            cfg = ENTITY_CONFIG.get(r.entity_type)
            min_score = cfg.min_score if cfg else 0.5

            if r.score < min_score:
                continue
            if span.lower() in FALSE_POSITIVE_WORDS:
                continue
            if r.entity_type == "PERSON":
                words = span.split()
                if len(words) < 2:
                    continue
                if any(w.isupper() and len(w) > 2 for w in words):
                    continue
            if r.entity_type == "LOCATION":
                if len(span) < 4:
                    continue
                if re.fullmatch(r"[0-9a-fA-F]{6,}", span):
                    continue

            kept.append(r)
        return kept


# ---------------------------------------------------------------------------
# Step 2 — Address
# ---------------------------------------------------------------------------

class AddressStep(PipelineStep):
    """Adds address hits found directly via regex.

    Presidio's NLP model is unreliable for German addresses, so this step
    adds regex-based hits on top of the NLP results. Full addresses
    (Musterstraße 12, 20095 Hamburg) are preferred over bare postal codes,
    which are only added when not already covered by a full address span.
    """

    def run(self, results: list[RecognizerResult], text: str) -> list[RecognizerResult]:
        regex_addresses: list[RecognizerResult] = []

        for m in ADDRESS_RE.finditer(text):
            regex_addresses.append(
                RecognizerResult("ADDRESS", m.start(), m.end(), 0.85)
            )

        address_spans = [(r.start, r.end) for r in regex_addresses]
        for m in PLZ_RE.finditer(text):
            covered = any(s <= m.start() and m.end() <= e for s, e in address_spans)
            if not covered:
                regex_addresses.append(
                    RecognizerResult("ADDRESS", m.start(), m.end(), 0.6)
                )

        return results + regex_addresses


# ---------------------------------------------------------------------------
# Step 3 — Trim person spans
# ---------------------------------------------------------------------------

class TrimPersonStep(PipelineStep):
    """Shortens PERSON spans that accidentally include a street keyword.

    Example: NLP flags "Max Mustermann Musterstraße" as a person.
    This step trims it to "Max Mustermann". If nothing useful remains
    after trimming, the result is discarded entirely.
    """

    def run(self, results: list[RecognizerResult], text: str) -> list[RecognizerResult]:
        trimmed = []
        for r in results:
            if r.entity_type == "PERSON":
                span = text[r.start : r.end]
                m = STREET_KEYWORDS.search(span)
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


# ---------------------------------------------------------------------------
# Step 4 — Propagate person names
# ---------------------------------------------------------------------------

class PropagatePersonStep(PipelineStep):
    """Re-scans the full text for every name already confirmed, catching
    repeated occurrences the NLP model may have missed.

    For example, if "Max Mustermann" is found at line 5, this step ensures
    it is also masked at line 20 even if the NLP missed it there.
    """

    def run(self, results: list[RecognizerResult], text: str) -> list[RecognizerResult]:
        known_names = self._extract_names(results, text)
        existing_spans = {(r.start, r.end) for r in results}
        propagated = []

        for name in known_names:
            if not name or len(name.split()) < 2:
                continue
            for m in re.finditer(re.escape(name), text):
                span = (m.start(), m.end())
                if span not in existing_spans:
                    propagated.append(
                        RecognizerResult("PERSON", m.start(), m.end(), 0.80)
                    )
                    existing_spans.add(span)

        return results + propagated

    @staticmethod
    def _extract_names(results: list[RecognizerResult], text: str) -> set[str]:
        """Collects confirmed person name strings, including pre-trim variants."""
        names: set[str] = set()
        for r in results:
            if r.entity_type != "PERSON":
                continue
            span = text[r.start : r.end].strip()
            names.add(span)
            m = STREET_KEYWORDS.search(span)
            if m:
                clean = span[: m.start()].strip()
                if clean:
                    names.add(clean)
        return names


# ---------------------------------------------------------------------------
# Step 5 — Resolve overlaps
# ---------------------------------------------------------------------------

class ResolveOverlapsStep(PipelineStep):
    """Resolves conflicts when two results overlap the same text span.

    Winner is determined by (priority, score) — higher wins.
    Priority is defined per entity type in ENTITY_CONFIG.

    Example: a span flagged as both LOCATION and ADDRESS → ADDRESS wins
    because it has higher priority.
    """

    def run(self, results: list[RecognizerResult], text: str) -> list[RecognizerResult]:
        def rank(r: RecognizerResult) -> tuple:
            cfg = ENTITY_CONFIG.get(r.entity_type)
            return (cfg.priority if cfg else 1, r.score)

        sorted_results = sorted(
            results,
            key=lambda r: (
                r.start,
                -(ENTITY_CONFIG[r.entity_type].priority if r.entity_type in ENTITY_CONFIG else 1),
                -r.score,
            ),
        )
        kept: list[RecognizerResult] = []
        for r in sorted_results:
            if not kept or r.start >= kept[-1].end:
                kept.append(r)
            elif rank(r) > rank(kept[-1]):
                kept[-1] = r
        return kept


# ---------------------------------------------------------------------------
# Default pipeline
# ---------------------------------------------------------------------------

DEFAULT_PIPELINE = MaskingPipeline([
    FilterStep(),           # 1. Remove noise first
    AddressStep(),          # 2. Add regex-based address hits
    TrimPersonStep(),       # 3. Fix person spans bleeding into street names
    PropagatePersonStep(),  # 4. Catch repeated names the NLP missed
    ResolveOverlapsStep(),  # 5. Resolve any conflicts across all results
])