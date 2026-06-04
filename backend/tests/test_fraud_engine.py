import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from app.models.member import Member
from app.schemas.claim_schema import AdjudicationContext, ExtractedData
from app.fraud.rule_fraud_engine import RuleFraudEngine
from app.database import IN_MEMORY_CLAIMS

@pytest.fixture(autouse=True)
def clear_in_memory_claims():
    IN_MEMORY_CLAIMS.clear()
    yield
    IN_MEMORY_CLAIMS.clear()

def test_rule_1_same_member_24h():
    member = Member(member_id="EMP001", name="John Doe", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE")
    engine = RuleFraudEngine()
    
    ctx = AdjudicationContext(
        claim_id="CLM_CURRENT",
        member=member,
        claim_amount=1000.0,
        treatment_date=date(2024, 6, 1),
        extracted_data=ExtractedData(diagnosis="Fever"),
    )
    
    # 1. No other claims
    signals = engine.detect(ctx)
    assert not any(s.signal_type == "MULTIPLE_CLAIMS_24H" for s in signals)
    assert not any(s.signal_type == "HIGH_FREQUENCY_CLAIMS_24H" for s in signals)
    
    # 2. Add one other claim within 24h
    IN_MEMORY_CLAIMS["CLM_PREV1"] = {
        "claim_id": "CLM_PREV1",
        "member_id": "EMP001",
        "treatment_date": date(2024, 6, 1),
        "extracted_data": ExtractedData(diagnosis="Headache")
    }
    signals = engine.detect(ctx)
    assert any(s.signal_type == "MULTIPLE_CLAIMS_24H" for s in signals)
    assert not any(s.signal_type == "HIGH_FREQUENCY_CLAIMS_24H" for s in signals)
    
    # 3. Add a third claim within 24h (2 other claims total)
    IN_MEMORY_CLAIMS["CLM_PREV2"] = {
        "claim_id": "CLM_PREV2",
        "member_id": "EMP001",
        "treatment_date": date(2024, 5, 31),
        "extracted_data": ExtractedData(diagnosis="Cough")
    }
    signals = engine.detect(ctx)
    assert any(s.signal_type == "HIGH_FREQUENCY_CLAIMS_24H" for s in signals)

def test_rule_2_same_provider_7d():
    member = Member(member_id="EMP001", name="John Doe", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE")
    engine = RuleFraudEngine()
    ctx = AdjudicationContext(
        claim_id="CLM_CURRENT",
        member=member,
        claim_amount=1000.0,
        treatment_date=date(2024, 6, 1),
        extracted_data=ExtractedData(diagnosis="Fever", provider_name="Apollo Clinic"),
    )
    
    # Add 4 claims for Apollo Clinic within 7 days
    for i in range(4):
        IN_MEMORY_CLAIMS[f"CLM_PROV_{i}"] = {
            "claim_id": f"CLM_PROV_{i}",
            "member_id": f"EMP_OTHER_{i}",
            "treatment_date": date(2024, 6, 1),
            "hospital_name": "Apollo Clinic",
            "extracted_data": ExtractedData(diagnosis="Fever")
        }
        
    signals = engine.detect(ctx)
    assert any(s.signal_type == "HIGH_FREQUENCY_PROVIDER_7D" for s in signals)

@patch("google.generativeai.GenerativeModel")
def test_rule_3_diagnosis_age_mismatch(mock_model_class):
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"mismatch_detected": true, "reasoning": "Pregnancy diagnosed in an infant"}'
    mock_model.generate_content.return_value = mock_response
    mock_model_class.return_value = mock_model
    
    with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
        member = Member(member_id="EMP001", name="John Doe", age=5, join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE")
        engine = RuleFraudEngine()
        ctx = AdjudicationContext(
            claim_id="CLM_CURRENT",
            member=member,
            claim_amount=1000.0,
            treatment_date=date(2024, 6, 1),
            extracted_data=ExtractedData(diagnosis="Pregnancy follow-up"),
        )
        signals = engine.detect(ctx)
        assert any(s.signal_type == "DIAGNOSIS_AGE_MISMATCH" for s in signals)

def test_rule_4_duplicate_bill_number():
    member = Member(member_id="EMP001", name="John Doe", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE")
    engine = RuleFraudEngine()
    ctx = AdjudicationContext(
        claim_id="CLM_CURRENT",
        member=member,
        claim_amount=1000.0,
        treatment_date=date(2024, 6, 1),
        extracted_data=ExtractedData(diagnosis="Fever", bill_number="BILL-999-123"),
    )
    
    # No duplicate
    signals = engine.detect(ctx)
    assert not any(s.signal_type == "DUPLICATE_BILL_NUMBER" for s in signals)
    
    # Add claim with same bill number
    IN_MEMORY_CLAIMS["CLM_PREV"] = {
        "claim_id": "CLM_PREV",
        "member_id": "EMP002",
        "treatment_date": date(2024, 5, 20),
        "extracted_data": ExtractedData(diagnosis="Fever", bill_number="BILL-999-123")
    }
    
    signals = engine.detect(ctx)
    assert any(s.signal_type == "DUPLICATE_BILL_NUMBER" for s in signals)
