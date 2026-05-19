from abc import ABC, abstractmethod
 
from presidio_analyzer import RecognizerResult

class PipelineStep(ABC):
    """Base class for a single masking pipeline step.
 
    Each step receives the current list of RecognizerResults plus the
    original text, and returns an updated list of RecognizerResults.
    Steps must not mutate the input list — return a new one.
    """
 
    @abstractmethod
    def run(
        self,
        results: list[RecognizerResult],
        text: str,
    ) -> list[RecognizerResult]:
        ...
 
 
class MaskingPipeline:
    """Runs a sequence of PipelineSteps in order.
 
    The step order matters — see DEFAULT_PIPELINE in steps.py for the
    rationale behind the default sequence.
 
    Args:
        steps: Ordered list of PipelineStep instances to execute.
 
    Example:
        pipeline = MaskingPipeline([FilterStep(), AddressStep()])
        results = pipeline.run(raw_results, text)
    """
 
    def __init__(self, steps: list[PipelineStep]) -> None:
        self.steps = steps
 
    def run(
        self,
        results: list[RecognizerResult],
        text: str,
    ) -> list[RecognizerResult]:
        for step in self.steps:
            results = step.run(results, text)
        return results