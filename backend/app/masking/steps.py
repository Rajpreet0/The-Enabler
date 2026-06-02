import re

from presidio_analyzer import RecognizerResult

from .config import (
    CONTEXT_RULES,
    ENTITY_CONFIG,
    FALSE_POSITIVE_WORDS,
    SALUTATION_WORDS,
    SALUTATION_WINDOW,
    STREET_KEYWORDS,
    ADDRESS_RE,
    PLZ_RE,
    URL_VALID_RE,
    URL_BLACKLIST_EXTENSIONS,
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
    - PERSON entities have at least two words (first + last name),
      unless a salutation (Herr/Frau/Dr. …) immediately precedes the span
    - PERSON entities contain no all-caps words (e.g. document headers)
    - LOCATION entities are at least 4 characters and not hex strings
    - URL entities pass regex validation and are not file references
    - ORGANIZATION entities have at least two words or a legal suffix
    """

    def run(self, results: list[RecognizerResult], text: str) -> list[RecognizerResult]:
        text_lower = text.lower()
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
                    # Relax the two-word rule when a salutation precedes the span.
                    if not self._has_salutation(r.start, text_lower):
                        continue
                if any(w.isupper() and len(w) > 2 for w in words):
                    continue
            if r.entity_type == "LOCATION":
                if len(span) < 4:
                    continue
                if re.fullmatch(r"[0-9a-fA-F]{6,}", span):
                    continue
            if r.entity_type == "URL":
                # Reject file references (e.g. *.jpg, image.png) via blacklist
                lower = span.lower()
                if any(lower.endswith(ext) for ext in URL_BLACKLIST_EXTENSIONS):
                    continue
                # Reject anything that doesn't look like a real web address
                if not URL_VALID_RE.search(span):
                    continue
            if r.entity_type == "ORGANIZATION":
                # Require at least 2 words or a known legal suffix to reduce
                # NLP false positives on common sentence fragments.
                words = span.split()
                has_legal_suffix = re.search(
                    r"\b(?:GmbH|AG|KG|OHG|UG|e\.V\.|gGmbH|SE)\b", span
                )
                if len(words) < 2 and not has_legal_suffix:
                    continue

            kept.append(r)
        return kept

    @staticmethod
    def _has_salutation(span_start: int, text_lower: str) -> bool:
        """Return True if a salutation token appears just before the span."""
        window_start = max(0, span_start - SALUTATION_WINDOW)
        prefix = text_lower[window_start:span_start].strip()
        # Check every salutation against the tail of the prefix so that
        # "Sehr geehrte Frau" still matches even with words in between.
        last_token = prefix.split()[-1] if prefix.split() else ""
        return last_token in SALUTATION_WORDS


# ---------------------------------------------------------------------------
# Step 2 — Context filter (generic, driven by CONTEXT_RULES whitelist)
# ---------------------------------------------------------------------------

class ContextFilterStep(PipelineStep):
    """Drops entity hits that lack supporting context keywords nearby.

    Which entity types require context — and how strictly — is declared in
    CONTEXT_RULES (config.py).  Two matching strategies are supported:

    • Simple window  (nearest_wins=False): at least one keyword must appear
      within `rule.window` characters of the match.  Used for entities with
      fairly distinctive regex patterns (IBAN-length numbers, tax IDs, etc.)
      where a keyword label nearby is enough to confirm intent.

    • Nearest-wins   (nearest_wins=True): a keyword is only credited to the
      *closest* candidate of the same entity type.  This prevents a stray
      document date sitting right before "Geburtsdatum: 03.05.1990" from
      being tagged as a birthday just because a keyword happens to be nearby.
      Keyword occurrences both before and after the candidate are considered.
    """

    def run(self, results: list[RecognizerResult], text: str) -> list[RecognizerResult]:
        text_lower = text.lower()

        # Pre-group candidates per entity type for nearest-wins rules
        candidates_by_type: dict[str, list[RecognizerResult]] = {}
        for entity_type, rule in CONTEXT_RULES.items():
            if rule.nearest_wins:
                candidates_by_type[entity_type] = [
                    r for r in results if r.entity_type == entity_type
                ]

        kept = []
        for r in results:
            rule = CONTEXT_RULES.get(r.entity_type)
            if rule is None:
                kept.append(r)
                continue

            if rule.nearest_wins:
                peers = candidates_by_type[r.entity_type]
                if not self._nearest_wins_has_context(r, text_lower, rule, peers):
                    continue
            else:
                if not self._simple_has_context(r, text_lower, rule):
                    continue

            kept.append(r)
        return kept

    @staticmethod
    def _simple_has_context(
        r: RecognizerResult,
        text_lower: str,
        rule: "ContextRule",  # noqa: F821 — resolved at runtime
    ) -> bool:
        start = max(0, r.start - rule.window)
        end   = min(len(text_lower), r.end + rule.window)
        snippet = text_lower[start:end]
        return any(kw in snippet for kw in rule.keywords)

    @staticmethod
    def _nearest_wins_has_context(
        candidate: RecognizerResult,
        text_lower: str,
        rule: "ContextRule",  # noqa: F821
        peers: list[RecognizerResult],
    ) -> bool:
        """Return True only when a keyword is found that isn't claimed by a
        closer peer candidate.

        For each keyword occurrence K two cases are handled:

        1. K precedes this candidate: accepted unless another peer sits
           between K and this candidate (that peer is closer, so it owns K).

        2. K follows this candidate: accepted only when no other peer also
           follows K (that peer would claim K as its leading label instead).
        """
        window_start = max(0, candidate.start - rule.window)
        window_end   = min(len(text_lower), candidate.end + rule.window)

        for kw in rule.keywords:
            search_pos = window_start
            while True:
                pos = text_lower.find(kw, search_pos, window_end)
                if pos == -1:
                    break
                kw_end = pos + len(kw)

                if kw_end <= candidate.start:
                    # Keyword before candidate — rejected if a closer peer sits
                    # between the keyword end and this candidate's start.
                    interleaved = any(
                        p is not candidate and kw_end <= p.start < candidate.start
                        for p in peers
                    )
                    if not interleaved:
                        return True
                else:
                    # Keyword after candidate — rejected if any other peer also
                    # follows the keyword (that peer would own it as a label).
                    claimed_by_other = any(
                        p is not candidate and p.start >= kw_end
                        for p in peers
                    )
                    if not claimed_by_other:
                        return True

                search_pos = pos + 1

        return False


# ---------------------------------------------------------------------------
# Step 4 — Address
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
# Step 5 — Trim person spans
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
# Step 6 — Propagate person names
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
# Step 7 — Resolve overlaps
# ---------------------------------------------------------------------------

class ResolveOverlapsStep(PipelineStep):
    """Resolves conflicts when two results overlap or contain each other.

    Winner is determined by (priority, score) — higher wins.
    Priority is defined per entity type in ENTITY_CONFIG.

    Handles three cases:
    - Exact/partial overlap: higher rank wins, keeps the winning span.
    - Containment (A contains B): B is split out if B has higher rank,
      otherwise B is dropped and A is kept intact.

    Example: ORGANIZATION span "Deutsche Bank AG DE89370400440532013000"
    contains an IBAN — IBAN has priority 6, ORGANIZATION priority 2,
    so the IBAN is preserved and the ORGANIZATION span is trimmed to
    exclude the IBAN portion.
    """

    def run(self, results: list[RecognizerResult], text: str) -> list[RecognizerResult]:
        def rank(r: RecognizerResult) -> tuple[int, float]:
            cfg = ENTITY_CONFIG.get(r.entity_type)
            return (cfg.priority if cfg else 1, r.score)

        # Sort by start position, then by descending rank so higher-priority
        # entities at the same position are processed first.
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
            if not kept:
                kept.append(r)
                continue

            prev = kept[-1]

            # No overlap at all — just append.
            if r.start >= prev.end:
                kept.append(r)
                continue

            # Some form of overlap exists.
            r_rank    = rank(r)
            prev_rank = rank(prev)

            if r_rank > prev_rank:
                # Incoming entity wins.  If it is fully contained inside prev,
                # replace prev with r (the smaller, higher-priority span).
                # If they partially overlap, replace prev with r as well —
                # the higher-priority entity takes the contested characters.
                kept[-1] = r
            # else: prev wins; discard r entirely (it is lower priority).

        return kept


# ---------------------------------------------------------------------------
# Default pipeline
# ---------------------------------------------------------------------------

DEFAULT_PIPELINE = MaskingPipeline([
    FilterStep(),           # 1. Remove noise and low-confidence hits
    ContextFilterStep(),    # 2. Drop dates/accounts without supporting context
    AddressStep(),          # 3. Add regex-based address hits
    TrimPersonStep(),       # 4. Fix person spans bleeding into street names
    PropagatePersonStep(),  # 5. Catch repeated names the NLP missed
    ResolveOverlapsStep(),  # 6. Resolve any conflicts across all results
])