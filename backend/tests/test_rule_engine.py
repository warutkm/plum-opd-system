import pytest
from datetime import date
from app.models.member import Member
from app.models.policy import PolicyTerms
from app.schemas.claim_schema import AdjudicationContext, ExtractedData
from app.engine.rule_engine import DeterministicRuleEngine
from app.models.claim import ClaimDecision


def test_engine_adjudicate_approved(base_policy):
    engine = DeterministicRuleEngine(base_policy)
    member = Member(member_id="EMP001", name="Rajesh Kumar", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE")
    ctx = AdjudicationContext(
        claim_id="CLM001",
        member=member,
        claim_amount=1500.0,
        treatment_date=date(2024, 6, 1),
        documents_submitted=["prescription", "bill"],
        extracted_data=ExtractedData(
            patient_name="Rajesh Kumar",
            doctor_registration="KA/45678/2015",
            diagnosis="Viral fever",
            treatment_date=date(2024, 6, 1),
            bill_amount=1500.0,
            bill_items={"consultation_fee": 1000, "diagnostic_tests": 500},
        ),
        bill_items={"consultation_fee": 1000, "diagnostic_tests": 500},
    )
    result = engine.adjudicate(ctx)
    assert result.decision == ClaimDecision.APPROVED
    assert result.approved_amount == 1350.0  # 1500 - 10% copay

def test_engine_adjudicate_rejected_waiting_period(base_policy):
    engine = DeterministicRuleEngine(base_policy)
    member = Member(member_id="EMP001", name="Rajesh Kumar", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE")
    ctx = AdjudicationContext(
        claim_id="CLM001",
        member=member,
        claim_amount=1500.0,
        treatment_date=date(2024, 1, 15),  # within initial waiting period
        documents_submitted=["prescription", "bill"],
        extracted_data=ExtractedData(
            patient_name="Rajesh Kumar",
            doctor_registration="KA/45678/2015",
            diagnosis="Viral fever",
            treatment_date=date(2024, 1, 15),
            bill_amount=1500.0,
        ),
    )
    result = engine.adjudicate(ctx)
    assert result.decision == ClaimDecision.REJECTED
    assert "WAITING_PERIOD" in result.rejection_reasons

def test_engine_adjudicate_partial(base_policy):
    engine = DeterministicRuleEngine(base_policy)
    member = Member(member_id="EMP001", name="Priya Singh", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE")
    ctx = AdjudicationContext(
        claim_id="CLM001",
        member=member,
        claim_amount=12000.0,
        treatment_date=date(2024, 6, 1),
        documents_submitted=["prescription", "bill"],
        extracted_data=ExtractedData(
            patient_name="Priya Singh",
            doctor_registration="MH/23456/2018",
            diagnosis="Tooth decay",
            procedures=["Root canal treatment", "Teeth whitening"],
            treatment_date=date(2024, 6, 1),
            bill_amount=12000.0,
            bill_items={"root_canal": 8000, "teeth_whitening": 4000},
        ),
        bill_items={"root_canal": 8000, "teeth_whitening": 4000},
    )
    result = engine.adjudicate(ctx)
    assert result.decision == ClaimDecision.PARTIAL
    assert result.approved_amount == 8000.0
    assert "Teeth whitening" in result.rejected_items
