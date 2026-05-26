"""Unit tests for individual pipeline steps (no NLP models required)."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import pytest
from presidio_analyzer import RecognizerResult
from masking.steps import ContextFilterStep


def _birthday(start: int, end: int) -> RecognizerResult:
    return RecognizerResult("BIRTHDAY", start, end, 0.85)


def _run(results, text):
    return ContextFilterStep().run(results, text)


# ---------------------------------------------------------------------------
# BIRTHDAY — nearest-date-wins context filter
# ---------------------------------------------------------------------------

class TestBirthdayContextFilter:

    def test_single_birthday_with_keyword_before(self):
        text = "Geburtsdatum: 03.05.1990"
        r = _birthday(14, 24)
        assert _run([r], text) == [r]

    def test_single_birthday_with_keyword_geb(self):
        text = "geb. 03.05.1990"
        r = _birthday(5, 15)
        assert _run([r], text) == [r]

    def test_single_birthday_no_keyword_rejected(self):
        text = "Datum: 03.05.1990"
        r = _birthday(7, 17)
        assert _run([r], text) == []

    def test_normal_date_before_birthday_rejected(self):
        """Core regression: plain date immediately before 'Geburtsdatum: XX' must not be tagged."""
        text = "Datum: 15.01.2024, Geburtsdatum: 03.05.1990"
        #       0      7        17   20          32  34       44
        normal_date = _birthday(7, 17)
        birth_date  = _birthday(33, 43)
        kept = _run([normal_date, birth_date], text)
        entity_spans = [(r.start, r.end) for r in kept]
        assert (7, 17) not in entity_spans,  "Normal date must NOT be tagged as BIRTHDAY"
        assert (33, 43) in entity_spans,     "Actual birthday must be tagged"

    def test_birthday_keyword_after_date_accepted(self):
        """'03.05.1990 (geb.)' — keyword is right after the date."""
        text = "03.05.1990 (geb.)"
        r = _birthday(0, 10)
        assert _run([r], text) == [r]

    def test_two_dates_one_keyword_nearest_wins(self):
        """Only the closer of two dates gets the keyword."""
        text = "15.01.2024 Geburtsdatum: 03.05.1990"
        #       0        10 11           24  25       35
        d1 = _birthday(0, 10)
        d2 = _birthday(25, 35)
        kept = _run([d1, d2], text)
        spans = [(r.start, r.end) for r in kept]
        assert (0, 10)  not in spans, "Farther date must not be tagged"
        assert (25, 35) in spans,     "Nearer date must be tagged"
