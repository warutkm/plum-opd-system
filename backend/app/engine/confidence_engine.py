"""
Confidence Engine — Point 8 from the architecture document.

Final confidence score:
    40% Extraction Confidence
    40% Rule Confidence
    20% Fraud / Document Quality

Example: 0.94

This directly addresses bonus criteria.
"""

from __future__ import annotations

from typing import Optional

from app.schemas.claim_schema import ExtractedData
from app.schemas.decision_schema import RuleEngineResult, ConfidenceBreakdown
from app.models.fraud import FraudResult


# ── Weights from the architecture document ────────────────────────────────
WEIGHT_EXTRACTION = 0.40
WEIGHT_RULE = 0.40
WEIGHT_FRAUD_DOC = 0.20

# If the fraud score exceeds this value, confidence is hard-capped
FRAUD_CONFIDENCE_CAP_THRESHOLD = 40.0
FRAUD_CONFIDENCE_CAP_VALUE = 0.65

# Below this confidence, the claim is flagged for manual review
LOW_CONFIDENCE_THRESHOLD = 0.70


class ConfidenceEngine:
    """Calculates the final pipeline confidence score.

    The confidence score is a weighted composite of three independent
    signals, each normalised to the [0, 1] range:

    1. **Extraction Confidence** (40 %)
       – How reliably the AI Extraction Agent parsed the claim documents.
       – Composite of field completeness, Gemini self-assessment, and
         data quality (date parsing, valid amounts, doctor registration).

    2. **Rule Confidence** (40 %)
       – How cleanly the claim passed through the deterministic rule engine.
       – 1.0 for a clean pass, reduced for soft violations (e.g. partial
         approval, documentation warnings).

    3. **Fraud / Document Quality** (20 %)
       – Combined measure of document validity and fraud risk.
       – A valid document set starts at 1.0; invalid drops to 0.5.
       – High-severity fraud signals further reduce this by 70 %.
       – The remaining value is multiplied by the inverse fraud score
         (0–100 mapped to 1.0–0.0).

    Safety Overrides
    ~~~~~~~~~~~~~~~~
    - **Fraud cap:** If the fraud score ≥ 40, the final confidence is
      hard-capped at 0.65 regardless of the other components.
    - **Low confidence flag:** If the final score falls below 0.70,
      the claim is recommended for MANUAL_REVIEW.
    """

    def calculate(
        self,
        extracted_data: ExtractedData,
        rule_result: RuleEngineResult,
        fraud_result: FraudResult,
        doc_status: str,
        has_high_fraud: bool,
    ) -> ConfidenceBreakdown:
        """Compute the final confidence score and return a full breakdown.

        Parameters
        ----------
        extracted_data : ExtractedData
            Contains ``extraction_confidence`` (0.0–1.0).
        rule_result : RuleEngineResult
            Contains ``rule_confidence`` (0.0–1.0).
        fraud_result : FraudResult
            Contains ``fraud_score`` (0–100).
        doc_status : str
            "PASS" if documents were validated successfully.
        has_high_fraud : bool
            True if any fraud signal has HIGH or CRITICAL severity.

        Returns
        -------
        ConfidenceBreakdown
            A Pydantic model with the individual component scores and
            the final weighted confidence.
        """
        # ── Component 1: Extraction Confidence (40 %) ─────────────────────
        extraction_conf = extracted_data.extraction_confidence

        # ── Component 2: Rule Confidence (40 %) ──────────────────────────
        rule_conf = rule_result.rule_confidence

        # ── Component 3: Fraud / Document Quality (20 %) ─────────────────
        doc_quality = 1.0 if doc_status == "PASS" else 0.5
        if has_high_fraud:
            doc_quality *= 0.3

        fraud_factor = max(0.0, (100.0 - fraud_result.fraud_score) / 100.0)
        fraud_doc_quality = doc_quality * fraud_factor

        # ── Weighted Sum ──────────────────────────────────────────────────
        final_confidence = (
            WEIGHT_EXTRACTION * extraction_conf
            + WEIGHT_RULE * rule_conf
            + WEIGHT_FRAUD_DOC * fraud_doc_quality
        )
        final_confidence = round(final_confidence, 2)

        # ── Safety Overrides ──────────────────────────────────────────────
        if fraud_result.fraud_score >= FRAUD_CONFIDENCE_CAP_THRESHOLD:
            final_confidence = min(final_confidence, FRAUD_CONFIDENCE_CAP_VALUE)

        return ConfidenceBreakdown(
            extraction_confidence=round(extraction_conf, 4),
            rule_confidence=round(rule_conf, 4),
            fraud_doc_quality=round(fraud_doc_quality, 4),
            final_confidence=final_confidence,
        )

    @staticmethod
    def should_flag_for_review(breakdown: ConfidenceBreakdown) -> bool:
        """Return True if the confidence score warrants manual review."""
        return breakdown.final_confidence < LOW_CONFIDENCE_THRESHOLD
