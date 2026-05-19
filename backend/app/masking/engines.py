from functools import lru_cache

from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

from .config import ADDRESS_RE, PLZ_RE
from .transformer_recognizer import GermanFlairNERRecognizer

# ---------------------------------------------------------------------------
# Custom recognizers — extend Presidio with German-specific regex patterns
# ---------------------------------------------------------------------------
 
def _build_address_recognizer() -> PatternRecognizer:
    return PatternRecognizer(
        supported_entity="ADDRESS",
        patterns=[
            Pattern(name="de_full_address", regex=ADDRESS_RE.pattern, score=0.85),
            Pattern(name="de_plz_ort",      regex=PLZ_RE.pattern,     score=0.6),
        ],
        supported_language="de",
    )
 
 
def _build_org_recognizer() -> PatternRecognizer:
    return PatternRecognizer(
        supported_entity="ORGANIZATION",
        patterns=[
            Pattern(
                name="de_org_suffix",
                regex=(
                    r"\b[A-ZÄÖÜ][A-Za-zäöüÄÖÜß&\s\-\.]{2,50}"
                    r"(?:GmbH|AG|KG|OHG|UG|e\.V\.|gGmbH|SE)(?:\s*&\s*Co\.?\s*KG)?\b"
                ),
                score=0.88,
            ),
        ],
        supported_language="de",
    )

# ---------------------------------------------------------------------------
# Engine initialisation — loaded once and cached for the process lifetime
# ---------------------------------------------------------------------------
 
@lru_cache(maxsize=1)
def get_engines() -> tuple[AnalyzerEngine, AnonymizerEngine]:
    """Initialise and cache the Presidio analyzer and anonymizer engines.
 
    Uses spaCy models for both English and German. The @lru_cache ensures
    the heavy NLP models are only loaded from disk once per process.
    """
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
    analyzer.registry.add_recognizer(GermanFlairNERRecognizer())
    anonymizer = AnonymizerEngine()
    return analyzer, anonymizer