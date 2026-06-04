"""
Decision Aggregator — combines rule engine results, fraud results,
and the Confidence Engine (Point 8) into a final claim decision.
"""

from __future__ import annotations

from typing import Tuple

from app.models.claim import ClaimDecision
from app.schemas.claim_schema import ExtractedData
from app.schemas.decision_schema import RuleEngineResult, ConfidenceBreakdown
from app.models.fraud import FraudResult
from app.engine.confidence_engine import ConfidenceEngine


class DecisionAggregator:
    """Aggregates rule engine output, fraud results, and confidence
    into the final claim decision.

    The confidence calculation is delegated to the ``ConfidenceEngine``
    (Point 8 of the architecture document).
    """

    def __init__(self) -> None:
        self.confidence_engine = ConfidenceEngine()

    def aggregate(
        self,
        extracted_data: ExtractedData,
        rule_result: RuleEngineResult,
        fraud_result: FraudResult,
        doc_status: str,
        has_high_fraud: bool,
    ) -> Tuple[str, float, str, str, ConfidenceBreakdown]:
        """Produce the final decision, confidence, next-steps, and notes.

        Returns
        -------
        Tuple of (decision, confidence, next_steps, notes, confidence_breakdown)
        """

        # ── Confidence Engine (Point 8) ───────────────────────────────────
        breakdown = self.confidence_engine.calculate(
            extracted_data, rule_result, fraud_result, doc_status, has_high_fraud
        )
        final_confidence = breakdown.final_confidence

        # ── Decision Logic ────────────────────────────────────────────────
        final_decision = rule_result.decision.value
        reasons = list(rule_result.rejection_reasons)
        notes = rule_result.notes

        if fraud_result.requires_manual_review:
            final_decision = ClaimDecision.MANUAL_REVIEW.value
            notes = f"Flagged by fraud engine (score: {fraud_result.fraud_score}). {notes}"
        elif self.confidence_engine.should_flag_for_review(breakdown):
            final_decision = ClaimDecision.MANUAL_REVIEW.value
            notes = f"Flagged due to low pipeline confidence ({final_confidence:.2f}). {notes}"

        # Hard rejections from the rule engine always take precedence
        if rule_result.decision == ClaimDecision.REJECTED:
            final_decision = ClaimDecision.REJECTED.value

        # ── Next Steps ────────────────────────────────────────────────────
        if final_decision == "APPROVED":
            next_steps = "Your claim has been approved. The approved amount will be processed for reimbursement."
        elif final_decision == "PARTIAL":
            next_steps = "Your claim has been partially approved. Excluded items have been rejected. You may appeal the excluded items."
        elif final_decision == "MANUAL_REVIEW":
            next_steps = "Your claim has been referred for manual review. An adjuster will audit the documents within 2 business days."
        else:
            next_steps = f"Your claim was rejected due to: {', '.join(reasons)}."

        return final_decision, final_confidence, next_steps, notes, breakdown