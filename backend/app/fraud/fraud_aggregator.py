"""
Fraud Score Aggregator — Point 7 from the architecture document.

Combines:
    • Rule-Based Fraud Signals
    • Vector Similarity Signals

Produces:
    • 0–100 fraud score
    • High score → MANUAL_REVIEW

Important Safety Rule (from architecture document):
    Vector fraud detection NEVER rejects claims.
    It may only:
        • Increase fraud score
        • Lower confidence
        • Route claim to MANUAL_REVIEW
"""

from __future__ import annotations

from typing import List

from app.models.fraud import FraudResult, FraudSignal, FraudEngine, FraudSeverity
from app.schemas.claim_schema import AdjudicationContext
from app.fraud.rule_fraud_engine import RuleFraudEngine
from app.fraud.vector_fraud_engine import VectorFraudEngine

# Threshold above which the claim is routed to MANUAL_REVIEW
MANUAL_REVIEW_THRESHOLD = 70.0


class FraudAggregator:
    """Aggregates fraud signals from both detection engines.

    The aggregator combines rule-based and vector similarity signals
    into a single 0-100 fraud score.  When the score exceeds 70,
    the claim is flagged for MANUAL_REVIEW.

    The vector similarity engine's safety rule is enforced here:
    its signals can only increase the score, lower confidence,
    or route to manual review — never directly reject.
    """

    def __init__(self, vector_model: str = "models/gemini-embedding-001"):
        self.rule_engine = RuleFraudEngine()
        self.vector_engine = VectorFraudEngine(vector_model)

    def detect(self, ctx: AdjudicationContext) -> FraudResult:
        """Run both fraud engines and aggregate results.

        Parameters
        ----------
        ctx : AdjudicationContext
            The claim context to evaluate.

        Returns
        -------
        FraudResult
            Combined fraud result with score, signals, and review flag.
        """
        signals: List[FraudSignal] = []

        # ── Engine 1: Rule-Based Fraud Detection ──────────────────────────
        rule_signals = self.rule_engine.detect(ctx)
        signals.extend(rule_signals)

        # ── Engine 2: Vector Similarity Fraud Detection ───────────────────
        vector_signals = self.vector_engine.detect(ctx)
        signals.extend(vector_signals)

        # ── Fraud Score Calculation ───────────────────────────────────────
        # Sum score impacts from both engines, capped at 100
        rule_impact = sum(
            sig.score_impact for sig in signals
            if sig.engine == FraudEngine.RULE_BASED
        )
        vector_impact = sum(
            sig.score_impact for sig in signals
            if sig.engine == FraudEngine.VECTOR_SIMILARITY
        )
        total_impact = rule_impact + vector_impact
        fraud_score = min(100.0, total_impact)

        # ── Manual Review Decision ────────────────────────────────────────
        requires_review = fraud_score >= MANUAL_REVIEW_THRESHOLD

        # ── Severity Analysis ─────────────────────────────────────────────
        severity_order = {
            FraudSeverity.LOW: 0,
            FraudSeverity.MEDIUM: 1,
            FraudSeverity.HIGH: 2,
            FraudSeverity.CRITICAL: 3,
        }
        highest_severity = max(
            (sig.severity for sig in signals),
            key=lambda s: severity_order.get(s, 0),
            default=FraudSeverity.LOW,
        )

        return FraudResult(
            fraud_score=fraud_score,
            signals=signals,
            requires_manual_review=requires_review,
            details={
                "total_signals": len(signals),
                "rule_based_signals": len(rule_signals),
                "vector_signals": len(vector_signals),
                "rule_based_impact": rule_impact,
                "vector_impact": vector_impact,
                "highest_severity": highest_severity.value,
            },
        )