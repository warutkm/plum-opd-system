import pytest
from app.services.decision_service import DecisionAggregator
from app.models.claim import ClaimDecision
from app.schemas.claim_schema import ExtractedData
from app.schemas.decision_schema import RuleEngineResult
from app.models.fraud import FraudResult

def test_decision_aggregator_approved():
    aggregator = DecisionAggregator()
    
    extracted_data = ExtractedData(extraction_confidence=0.95, doctor_registration="KA/12345/2015", bill_amount=1500)
    rule_result = RuleEngineResult(
        decision=ClaimDecision.APPROVED,
        approved_amount=1350.0,
        rejection_reasons=[],
        notes="Standard approval"
    )
    fraud_result = FraudResult(
        fraud_score=10.0,
        signals=[],
        requires_manual_review=False
    )
    
    decision, confidence, next_steps, notes, breakdown = aggregator.aggregate(
        extracted_data, rule_result, fraud_result, doc_status="PASS", has_high_fraud=False
    )
    
    assert decision == "APPROVED"
    assert confidence >= 0.70
    assert "approved" in next_steps.lower()

def test_decision_aggregator_rejected():
    aggregator = DecisionAggregator()
    
    extracted_data = ExtractedData(extraction_confidence=0.95)
    rule_result = RuleEngineResult(
        decision=ClaimDecision.REJECTED,
        approved_amount=0.0,
        rejection_reasons=["MISSING_DOCUMENTS"],
        notes="Required documents missing"
    )
    fraud_result = FraudResult(
        fraud_score=10.0,
        signals=[],
        requires_manual_review=False
    )
    
    decision, confidence, next_steps, notes, breakdown = aggregator.aggregate(
        extracted_data, rule_result, fraud_result, doc_status="FAIL", has_high_fraud=False
    )
    
    assert decision == "REJECTED"
    assert "rejected" in next_steps.lower()

def test_decision_aggregator_manual_review_due_to_fraud():
    aggregator = DecisionAggregator()
    
    extracted_data = ExtractedData(extraction_confidence=0.95, doctor_registration="KA/12345/2015", bill_amount=1500)
    rule_result = RuleEngineResult(
        decision=ClaimDecision.APPROVED,
        approved_amount=1350.0,
        rejection_reasons=[],
        notes="Standard approval"
    )
    fraud_result = FraudResult(
        fraud_score=85.0,
        signals=[],
        requires_manual_review=True
    )
    
    decision, confidence, next_steps, notes, breakdown = aggregator.aggregate(
        extracted_data, rule_result, fraud_result, doc_status="PASS", has_high_fraud=True
    )
    
    assert decision == "MANUAL_REVIEW"
    assert "manual review" in next_steps.lower()

def test_decision_aggregator_manual_review_due_to_low_confidence():
    aggregator = DecisionAggregator()
    
    # Low extraction confidence causes composite confidence to drop below 0.70
    extracted_data = ExtractedData(extraction_confidence=0.30, doctor_registration="KA/12345/2015", bill_amount=1500)
    rule_result = RuleEngineResult(
        decision=ClaimDecision.APPROVED,
        approved_amount=1350.0,
        rejection_reasons=[],
        notes="Standard approval"
    )
    fraud_result = FraudResult(
        fraud_score=10.0,
        signals=[],
        requires_manual_review=False
    )
    
    decision, confidence, next_steps, notes, breakdown = aggregator.aggregate(
        extracted_data, rule_result, fraud_result, doc_status="PASS", has_high_fraud=False
    )
    
    assert decision == "MANUAL_REVIEW"
    assert confidence < 0.70
    assert "manual review" in next_steps.lower()
