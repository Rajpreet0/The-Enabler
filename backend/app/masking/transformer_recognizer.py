from functools import lru_cache
from typing import Optional

from presidio_analyzer import EntityRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpArtifacts

_LABEL_MAP: dict[str, str] = {
    "PER": "PERSON",
    "ORG": "ORGANIZATION",
    "LOC": "LOCATION",
}


@lru_cache(maxsize=1)
def _load_tagger():
    from flair.models import SequenceTagger  # imported lazily to avoid slowing down startup

    return SequenceTagger.load("flair/ner-german-large")


class GermanFlairNERRecognizer(EntityRecognizer):
    """Flair-based German NER recognizer using flair/ner-german-large.

    Wraps the Flair SequenceTagger as a Presidio EntityRecognizer.
    The model is downloaded on first use and cached for the process lifetime.
    """

    def __init__(self) -> None:
        super().__init__(
            supported_entities=list(_LABEL_MAP.values()),
            supported_language="de",
            name="GermanFlairNERRecognizer",
        )

    def load(self) -> None:
        pass

    def analyze(
        self,
        text: str,
        entities: list[str],
        nlp_artifacts: Optional[NlpArtifacts] = None,
    ) -> list[RecognizerResult]:
        from flair.data import Sentence

        tagger = _load_tagger()
        sentence = Sentence(text)
        tagger.predict(sentence)

        results: list[RecognizerResult] = []
        for span in sentence.get_spans("ner"):
            presidio_type = _LABEL_MAP.get(span.tag)
            if presidio_type and presidio_type in entities:
                results.append(
                    RecognizerResult(
                        entity_type=presidio_type,
                        start=span.start_position,
                        end=span.end_position,
                        score=span.score,
                    )
                )
        return results
