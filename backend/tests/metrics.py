from dataclasses import dataclass
from collections import defaultdict

# =====================================================================
# 1. METRICS HOLDER
# =====================================================================
# A @dataclass is just a blueprint for a clean container that holds data.
# This class acts like a scorecard for True Positive (tp), False Positives (fp)
# and False Negatives (fn).
@dataclass
class Metrics:
    tp: int = 0     # Correctly found PII (e.g. "Müller", found as NAME)
    fp: int = 0     # Wrongly found PII   (e.g. "GmbH" flagged as NAME)
    fn: int = 0     # Missed PII          (e.g. "Sommer" missed entirely)

    # --- Properties (Calculated automatically when requested) --- 

    @property
    def precision(self) -> float:
        # Precision: "Out of everything the pipeline found, how much was actually corrected?"
        # Formula: tp / (tp + fp)
        # The 'if' part prevents a crash (divison by zero) if nothing was found.
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        # Recall: "Out of all the PII that actually exists, how much did the pipeline catch?"
        # Formula: tp / (tp + fn)
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        # F1-Score: The balance/average between Precision and Recall
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    def __add__(self, other: "Metrics") -> "Metrics":
        # This lets us combine scores easily using the + sign
        # Example: total_score = score_for_names + score_for_ibans
        return Metrics(
            tp=self.tp + other.tp,
            fp=self.fp + other.fp,
            fn=self.fn + other.fn,
        )

# =====================================================================
# 2. OVERLAP HELPER
# =====================================================================
def _overlaps(pred: dict, gt: dict, threshold: float = 0.5) -> bool:
    """
        Checks if a predicted text span overlaps enough with the Ground Truth (real PII).
        Example:
            Ground Truth: "Dr. med. Christiane Sommer" (characters 10 to 36)
            Prediction:   "Christiane Sommer"          (characters 19 to 36)
    """

    # 1. Calculate how many characters they share in common (intersection)
    overlap = max(0, min(pred["end"], gt["end"]) - max(pred["start"], gt["start"]))

    # 2. Calculate the full length of the real PII
    gt_len  = gt["end"] - gt["start"]

    # 3. Return True if the overlap covers at least 50% (threshold) of the real PII
    return gt_len > 0 and (overlap / gt_len) >= threshold


# =====================================================================
# 3. MAIN EVALUATION ENGINE
# =====================================================================
def compute_metrics(
    predictions: list[dict],
    ground_truth: list[dict],
    overlap_threshold: float = 0.5,
) -> tuple[dict[str, Metrics], Metrics]:
    """
        Compares what the pipeline found (predictions) against the real data (ground_truth).
        It counts TPs, FPs, and FNs per PII category (e.g. EMAIL, IBAN, NAME) and overall
    """
    # Create an empty scorecard dictionary that automatically sets up
    # a new "Metrics" object the first time it sees a new PII type
    per_type: dict[str, Metrics] = defaultdict(Metrics)

    # Keep track of which real PII items we already successfully matched
    # so we don't accidentally count the same real PII twice.
    matched_gt: set[int] = set()

    # -----------------------------------------------------------------
    # STEP A: Loop through everything your PII Pipeline found
    # -----------------------------------------------------------------
    for pred in predictions:
        etype = pred["entity_type"]     # e.g. EMAIL

        # Look into the real data to see if there is a matching, unmatched item
        matched = any(
            i not in matched_gt
            and gt["entity_type"] == etype
            and _overlaps(pred, gt, overlap_threshold)
            for i, gt in enumerate(ground_truth)
            if gt["entity_type"] == etype
        )
        if matched:
            # If a match is found, find that exact real PII item again...
            for i, gt in enumerate(ground_truth):
                if (
                    i not in matched_gt
                    and gt["entity_type"] == etype
                    and _overlaps(pred, gt, overlap_threshold)
                ):
                    matched_gt.add(i)   # ... and mark it as "used up"
                    break

            # Add +1 to True Positives (TP) for this PII type 
            per_type[etype] = Metrics(
                tp=per_type[etype].tp + 1,
                fp=per_type[etype].fp,
                fn=per_type[etype].fn,
            )
        else:
            # If the pipeline found something but it wasn't in the real data,
            # add +1 to False Positives (FP) for this PII type
            per_type[etype] = Metrics(
                tp=per_type[etype].tp,
                fp=per_type[etype].fp + 1,
                fn=per_type[etype].fn,
            )

    # -----------------------------------------------------------------
    # STEP B: Look for missed PII
    # -----------------------------------------------------------------
    # Look through the real data. If anything was left unmatched
    # the pipeline missed it.
    for i, gt in enumerate(ground_truth):
        if i not in matched_gt:
            etype = gt["entity_type"]
            # Add +1 to False Negatives (FN) for this PII type
            per_type[etype] = Metrics(
                tp=per_type[etype].tp,
                fp=per_type[etype].fp,
                fn=per_type[etype].fn + 1,
            )

    # -----------------------------------------------------------------
    # STEP C: Generate Final Totals
    # -----------------------------------------------------------------
    # Sum up all the individual category scores to get one grand total
    overall = sum(per_type.values(), Metrics())

    # Return a dictionary with results per category, and the overall summary
    return dict(per_type), overall
