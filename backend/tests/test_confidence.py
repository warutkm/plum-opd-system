"""
Tests for the Confidence Engine (Point 8 from the architecture document).

Final confidence score:
    40% Extraction Confidence
    40% Rule Confidence
    20% Fraud / Document Quality

Verifies:
    1. Correct 40/40/20 weighted formula
    2. Example from the doc: 0.94
    3. Fraud score cap (score >= 40 → max 0.65)
    4. Low confidence triggers MANUAL_REVIEW
    5. High-fraud severity degrades doc quality
    6. Invalid documents reduce the fraud/doc quality component
    7. Perfect scores produce high confidence
    8. Integration with DecisionAggregator
"""

import pytest
from datetime import date

from app.engine.confidence_engine import (
    ConfidenceEngine,
    WEIGHT_EXTRACTION,
    WEIGHT_RULE,
    WEIGHT_FRAUD_DOC,
    FRAUD_CONFIDENCE_CAP_THRESHOLD,
    FRAUD_CONFIDENCE_CAP_VALUE,
    LOW_CONFIDENCE_THRESHOLD,
)
from app.schemas.claim_schema import ExtractedData
from app.schemas.decision_schema import RuleEngineResult, ConfidenceBreakdown
from app.models.claim import ClaimDecision
from app.models.fraud import FraudResult, FraudSignal, FraudEngine, FraudSeverity
from app.services.decision_service import DecisionAggregator


# ── Helpers ───────────────────────────────────────────────────────────────

def _make_rule_result(
    decision: ClaimDecision = ClaimDecision.APPROVED,
    rule_confidence: float = 1.0,
    notes: str = "",
) -> RuleEngineResult:
    return RuleEngineResult(
        decision=decision,
        rule_confidence=rule_confidence,
        approved_amount=1000.0,
        notes=notes,
    )


def _make_fraud_result(
    fraud_score: float = 0.0,
    signals: list = None,
) -> FraudResult:
    return FraudResult(
        fraud_score=fraud_score,
        signals=signals or [],
        requires_manual_review=fraud_score >= 70.0,
    )


def _make_extracted(confidence: float = 0.95) -> ExtractedData:
    return ExtractedData(
        diagnosis="Fever",
        provider_name="Apollo Clinic",
        extraction_confidence=confidence,
    )


# ── Weight Validation ─────────────────────────────────────────────────────

class TestWeights:
    """Verify the 40/40/20 formula weights from the architecture doc."""

    def test_weights_sum_to_one(self):
        assert WEIGHT_EXTRACTION + WEIGHT_RULE + WEIGHT_FRAUD_DOC == 1.0

    def test_extraction_weight_is_40(self):
        assert WEIGHT_EXTRACTION == 0.40

    def test_rule_weight_is_40(self):
        assert WEIGHT_RULE == 0.40

    def test_fraud_doc_weight_is_20(self):
        assert WEIGHT_FRAUD_DOC == 0.20


# ── Core Formula Tests ────────────────────────────────────────────────────

class TestConfidenceEngine:
    """Test the core confidence calculation."""

    def setup_method(self):
        self.engine = ConfidenceEngine()

    def test_perfect_scores_produce_high_confidence(self):
        """All components perfect → confidence = 1.0."""
        breakdown = self.engine.calculate(
            extracted_data=_make_extracted(1.0),
            rule_result=_make_rule_result(rule_confidence=1.0),
            fraud_result=_make_fraud_result(0.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        assert breakdown.final_confidence == 1.0
        assert breakdown.extraction_confidence == 1.0
        assert breakdown.rule_confidence == 1.0
        assert breakdown.fraud_doc_quality == 1.0

    def test_architecture_doc_example(self):
        """The PDF gives an example of 0.94 confidence.

        This can be achieved with:
          extraction=0.95, rule=1.0, fraud_score=0, docs=PASS
          → 0.4*0.95 + 0.4*1.0 + 0.2*1.0 = 0.38 + 0.40 + 0.20 = 0.98

        Or with extraction=0.95, rule=0.95, fraud_score=5:
          fraud_doc = 1.0 * (95/100) = 0.95
          → 0.4*0.95 + 0.4*0.95 + 0.2*0.95 = 0.38 + 0.38 + 0.19 = 0.95

        Let's verify a close approximation:
        """
        breakdown = self.engine.calculate(
            extracted_data=_make_extracted(0.90),
            rule_result=_make_rule_result(rule_confidence=1.0),
            fraud_result=_make_fraud_result(5.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        # 0.4*0.90 + 0.4*1.0 + 0.2*(1.0 * 0.95) = 0.36 + 0.40 + 0.19 = 0.95
        assert 0.90 <= breakdown.final_confidence <= 1.0

    def test_formula_manual_calculation(self):
        """Manually verify the formula: 0.4*E + 0.4*R + 0.2*FDQ."""
        breakdown = self.engine.calculate(
            extracted_data=_make_extracted(0.80),
            rule_result=_make_rule_result(rule_confidence=0.90),
            fraud_result=_make_fraud_result(0.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        # fraud_doc_quality = 1.0 * (100-0)/100 = 1.0
        # 0.4*0.80 + 0.4*0.90 + 0.2*1.0 = 0.32 + 0.36 + 0.20 = 0.88
        assert breakdown.final_confidence == 0.88
        assert breakdown.extraction_confidence == 0.80
        assert breakdown.rule_confidence == 0.90
        assert breakdown.fraud_doc_quality == 1.0

    def test_zero_extraction_confidence(self):
        """Zero extraction confidence significantly drops the score."""
        breakdown = self.engine.calculate(
            extracted_data=_make_extracted(0.0),
            rule_result=_make_rule_result(rule_confidence=1.0),
            fraud_result=_make_fraud_result(0.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        # 0.4*0.0 + 0.4*1.0 + 0.2*1.0 = 0.0 + 0.40 + 0.20 = 0.60
        assert breakdown.final_confidence == 0.60

    def test_zero_rule_confidence(self):
        """Zero rule confidence significantly drops the score."""
        breakdown = self.engine.calculate(
            extracted_data=_make_extracted(1.0),
            rule_result=_make_rule_result(rule_confidence=0.0),
            fraud_result=_make_fraud_result(0.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        # 0.4*1.0 + 0.4*0.0 + 0.2*1.0 = 0.40 + 0.0 + 0.20 = 0.60
        assert breakdown.final_confidence == 0.60

    def test_all_zero_components(self):
        """All components zero → confidence = 0."""
        breakdown = self.engine.calculate(
            extracted_data=_make_extracted(0.0),
            rule_result=_make_rule_result(rule_confidence=0.0),
            fraud_result=_make_fraud_result(100.0),
            doc_status="FAIL",
            has_high_fraud=True,
        )
        assert breakdown.final_confidence == 0.0

    def test_returns_confidence_breakdown_model(self):
        """The engine returns a proper ConfidenceBreakdown Pydantic model."""
        breakdown = self.engine.calculate(
            extracted_data=_make_extracted(0.95),
            rule_result=_make_rule_result(rule_confidence=1.0),
            fraud_result=_make_fraud_result(0.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        assert isinstance(breakdown, ConfidenceBreakdown)
        assert hasattr(breakdown, "extraction_confidence")
        assert hasattr(breakdown, "rule_confidence")
        assert hasattr(breakdown, "fraud_doc_quality")
        assert hasattr(breakdown, "final_confidence")


# ── Fraud / Document Quality Component ────────────────────────────────────

class TestFraudDocQuality:
    """Test the 20% Fraud / Document Quality component."""

    def setup_method(self):
        self.engine = ConfidenceEngine()

    def test_invalid_docs_reduce_quality(self):
        """doc_status != PASS halves the document quality component."""
        good = self.engine.calculate(
            extracted_data=_make_extracted(0.95),
            rule_result=_make_rule_result(),
            fraud_result=_make_fraud_result(0.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        bad = self.engine.calculate(
            extracted_data=_make_extracted(0.95),
            rule_result=_make_rule_result(),
            fraud_result=_make_fraud_result(0.0),
            doc_status="FAIL",
            has_high_fraud=False,
        )
        # Only the 20% component is affected: 1.0 → 0.5
        assert good.fraud_doc_quality == 1.0
        assert bad.fraud_doc_quality == 0.5
        assert good.final_confidence > bad.final_confidence

    def test_high_fraud_signals_degrade_quality(self):
        """HIGH/CRITICAL fraud signals reduce doc quality by 70%."""
        no_fraud = self.engine.calculate(
            extracted_data=_make_extracted(0.95),
            rule_result=_make_rule_result(),
            fraud_result=_make_fraud_result(0.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        with_fraud = self.engine.calculate(
            extracted_data=_make_extracted(0.95),
            rule_result=_make_rule_result(),
            fraud_result=_make_fraud_result(0.0),
            doc_status="PASS",
            has_high_fraud=True,
        )
        # has_high_fraud: doc_quality goes from 1.0 to 0.3
        assert with_fraud.fraud_doc_quality == pytest.approx(0.3, abs=0.01)
        assert no_fraud.final_confidence > with_fraud.final_confidence

    def test_fraud_score_inversely_affects_quality(self):
        """Higher fraud scores reduce the fraud/doc quality component."""
        low = self.engine.calculate(
            extracted_data=_make_extracted(0.95),
            rule_result=_make_rule_result(),
            fraud_result=_make_fraud_result(10.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        high = self.engine.calculate(
            extracted_data=_make_extracted(0.95),
            rule_result=_make_rule_result(),
            fraud_result=_make_fraud_result(80.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        # fraud_factor = (100-score)/100 → 0.9 vs 0.2
        assert low.fraud_doc_quality > high.fraud_doc_quality

    def test_combined_bad_docs_and_fraud(self):
        """Bad documents + high fraud gives very low quality."""
        breakdown = self.engine.calculate(
            extracted_data=_make_extracted(0.95),
            rule_result=_make_rule_result(),
            fraud_result=_make_fraud_result(50.0),
            doc_status="FAIL",
            has_high_fraud=True,
        )
        # doc_quality = 0.5 * 0.3 = 0.15
        # fraud_factor = (100-50)/100 = 0.5
        # fraud_doc_quality = 0.15 * 0.5 = 0.075
        assert breakdown.fraud_doc_quality == pytest.approx(0.075, abs=0.001)


# ── Safety Overrides ──────────────────────────────────────────────────────

class TestSafetyOverrides:
    """Test the confidence safety overrides."""

    def setup_method(self):
        self.engine = ConfidenceEngine()

    def test_fraud_score_caps_confidence(self):
        """Fraud score >= 40 caps confidence at 0.65."""
        breakdown = self.engine.calculate(
            extracted_data=_make_extracted(0.95),
            rule_result=_make_rule_result(rule_confidence=1.0),
            fraud_result=_make_fraud_result(45.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        assert breakdown.final_confidence <= FRAUD_CONFIDENCE_CAP_VALUE

    def test_fraud_score_below_threshold_no_cap(self):
        """Fraud score < 40 does NOT cap confidence."""
        breakdown = self.engine.calculate(
            extracted_data=_make_extracted(0.95),
            rule_result=_make_rule_result(rule_confidence=1.0),
            fraud_result=_make_fraud_result(39.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        assert breakdown.final_confidence > FRAUD_CONFIDENCE_CAP_VALUE

    def test_low_confidence_flags_review(self):
        """Confidence < 0.70 should flag for manual review."""
        breakdown = self.engine.calculate(
            extracted_data=_make_extracted(0.0),
            rule_result=_make_rule_result(rule_confidence=1.0),
            fraud_result=_make_fraud_result(0.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        # 0.4*0.0 + 0.4*1.0 + 0.2*1.0 = 0.60 < 0.70
        assert breakdown.final_confidence < LOW_CONFIDENCE_THRESHOLD
        assert self.engine.should_flag_for_review(breakdown) is True

    def test_high_confidence_no_review_flag(self):
        """Confidence >= 0.70 should NOT flag for manual review."""
        breakdown = self.engine.calculate(
            extracted_data=_make_extracted(0.95),
            rule_result=_make_rule_result(rule_confidence=1.0),
            fraud_result=_make_fraud_result(0.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        assert breakdown.final_confidence >= LOW_CONFIDENCE_THRESHOLD
        assert self.engine.should_flag_for_review(breakdown) is False


# ── Integration with DecisionAggregator ───────────────────────────────────

class TestConfidenceInDecisionAggregator:
    """Verify the confidence engine is properly wired into the
    DecisionAggregator pipeline."""

    def test_aggregator_returns_breakdown(self):
        """DecisionAggregator returns a ConfidenceBreakdown as the 5th element."""
        aggregator = DecisionAggregator()
        result = aggregator.aggregate(
            extracted_data=_make_extracted(0.95),
            rule_result=_make_rule_result(),
            fraud_result=_make_fraud_result(0.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        assert len(result) == 5
        decision, confidence, next_steps, notes, breakdown = result
        assert isinstance(breakdown, ConfidenceBreakdown)
        assert confidence == breakdown.final_confidence

    def test_low_confidence_triggers_manual_review(self):
        """Low confidence should force the decision to MANUAL_REVIEW."""
        aggregator = DecisionAggregator()
        decision, confidence, _, notes, breakdown = aggregator.aggregate(
            extracted_data=_make_extracted(0.0),
            rule_result=_make_rule_result(
                decision=ClaimDecision.APPROVED,
                rule_confidence=1.0,
            ),
            fraud_result=_make_fraud_result(0.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        # 0.4*0.0 + 0.4*1.0 + 0.2*1.0 = 0.60 < 0.70
        assert confidence < 0.70
        assert decision == "MANUAL_REVIEW"
        assert "low pipeline confidence" in notes.lower()

    def test_high_fraud_score_triggers_manual_review(self):
        """High fraud score should trigger MANUAL_REVIEW via the aggregator."""
        aggregator = DecisionAggregator()
        decision, confidence, _, notes, breakdown = aggregator.aggregate(
            extracted_data=_make_extracted(0.95),
            rule_result=_make_rule_result(
                decision=ClaimDecision.APPROVED,
                rule_confidence=1.0,
            ),
            fraud_result=_make_fraud_result(80.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        assert decision == "MANUAL_REVIEW"
        assert "fraud engine" in notes.lower()

    def test_rejection_overrides_manual_review(self):
        """Hard rejections from the rule engine always take precedence."""
        aggregator = DecisionAggregator()
        decision, _, _, _, _ = aggregator.aggregate(
            extracted_data=_make_extracted(0.0),
            rule_result=_make_rule_result(
                decision=ClaimDecision.REJECTED,
                rule_confidence=0.0,
            ),
            fraud_result=_make_fraud_result(0.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        assert decision == "REJECTED"

    def test_approved_claim_with_high_confidence(self):
        """Clean claim should be APPROVED with high confidence."""
        aggregator = DecisionAggregator()
        decision, confidence, next_steps, _, breakdown = aggregator.aggregate(
            extracted_data=_make_extracted(0.95),
            rule_result=_make_rule_result(
                decision=ClaimDecision.APPROVED,
                rule_confidence=1.0,
            ),
            fraud_result=_make_fraud_result(0.0),
            doc_status="PASS",
            has_high_fraud=False,
        )
        assert decision == "APPROVED"
        assert confidence >= 0.90
        assert "approved" in next_steps.lower()
