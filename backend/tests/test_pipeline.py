import sys
import threading
import itertools
import time

import pytest
from conftest import all_doc_names
from metrics import compute_metrics


class _Spinner:
    def __init__(self, message: str):
        self._message = message
        self._stop    = threading.Event()
        self._thread  = threading.Thread(target=self._spin, daemon=True)

    def _spin(self):
        for frame in itertools.cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]):
            if self._stop.is_set():
                break
            sys.stderr.write(f"\r  {frame}  {self._message} ")
            sys.stderr.flush()
            time.sleep(0.1)
        sys.stderr.write("\r" + " " * (len(self._message) + 8) + "\r")
        sys.stderr.flush()

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join()

# The minimum acceptable F1-score (60%)
# If your pipeline scores lower than this, the test fails.
BASELINE_F1 = 0.60

# =====================================================================
# TEST 1: Check each document individually
# =====================================================================
# '@pytest.mark.parametrize' is a loop runner. It tells pytest:
# "Run this test function multiple times, once for every document found in all_doc_names()".
# (e.g., once for cv.txt, once for invoice.txt, etc.)
@pytest.mark.parametrize("doc_name", all_doc_names())
def test_document_f1(doc_name, pipeline, annotation):
    # 1. Get predictions from the pipeline and correct answers from annotations
    with _Spinner(f"Running pipeline on {doc_name}"):
        predictions  = pipeline(doc_name)
    ground_truth = annotation(doc_name)

    # 2. Run the math engine to get the scorecard (per type and overall)
    per_type, overall = compute_metrics(predictions, ground_truth)
    
    # 3. PRINTING A VISUAL REPORT (Formatting table headers)
    print(f"\n{'─' * 50}")
    print(f"Document: {doc_name}")
    print(f"{'─' * 50}")
    print(f"  {'Entity Type':<22} {'P':>6} {'R':>6} {'F1':>6}  TP  FP  FN")
    print(f"  {'─'*22} {'─'*6} {'─'*6} {'─'*6}  {'─'*2}  {'─'*2}  {'─'*2}")

    # 4. Print results for every individual PII type found (e.g., EMAIL, NAME)
    for etype, m in sorted(per_type.items()):
        print(
            f"  {etype:<22} {m.precision:>6.2f} {m.recall:>6.2f} {m.f1:>6.2f}"
            f"  {m.tp:>2}  {m.fp:>2}  {m.fn:>2}"
        )
    print(f"  {'─'*22} {'─'*6} {'─'*6} {'─'*6}  {'─'*2}  {'─'*2}  {'─'*2}")

    # 5. Print the overall summary line for this single document
    print(
        f"  {'OVERALL':<22} {overall.precision:>6.2f} {overall.recall:>6.2f} {overall.f1:>6.2f}"
        f"  {overall.tp:>2}  {overall.fp:>2}  {overall.fn:>2}"
    )

    # 6. THE DECISION: Check if the overall F1-score meets the 60% requirement.
    # 'assert' means: "This MUST be True. If it is False, stop and raise an error."
    assert overall.f1 >= BASELINE_F1, (
        f"Regression on '{doc_name}': F1={overall.f1:.2f} < baseline {BASELINE_F1}"
    )

# =====================================================================
# TEST 2: Check total score across ALL documents combined
# =====================================================================
def test_overall_f1(pipeline, annotation):
    from metrics import Metrics

    # Create an empty, clean global scorecard   
    combined = Metrics()

    # Loop through every single document and add their scores together
    for doc_name in all_doc_names():
        with _Spinner(f"Running pipeline on {doc_name}"):
            predictions = pipeline(doc_name)
        ground_truth = annotation(doc_name)
        _, overall = compute_metrics(predictions, ground_truth)

        # This uses the custom '+' feature we defined in the very first script!
        combined = combined + overall

    # Print a combined grand total summary table
    print(f"\nOVERALL ACROSS ALL DOCUMENTS:")
    print(f"  P={combined.precision:.2f}  R={combined.recall:.2f}  F1={combined.f1:.2f}")
    print(f"  TP={combined.tp}  FP={combined.fp}  FN={combined.fn}")

    # Check if the grand total score is also above 60%
    assert combined.f1 >= BASELINE_F1, (
        f"Overall regression: F1={combined.f1:2.f} < baseline {BASELINE_F1}"
    )
