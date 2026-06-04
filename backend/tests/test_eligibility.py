from datetime import date, timedelta
import pytest
from app.models.member import Member
from app.models.policy import PolicyTerms
from app.schemas.claim_schema import AdjudicationContext, ExtractedData
from app.engine.eligibility import run_eligibility_module


def test_inactive_member(base_policy):
    member = Member(member_id="EMP001", name="John Doe", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE", is_active=False)
    ctx = AdjudicationContext(
        claim_id="CLM001",
        member=member,
        claim_amount=1000.0,
        treatment_date=date(2024, 6, 1),
        extracted_data=ExtractedData(diagnosis="Viral fever"),
    )
    result = run_eligibility_module(ctx, base_policy)
    assert not result.passed
    assert result.status == "FAIL"
    assert "POLICY_INACTIVE" in result.rejection_reasons

def test_policy_mismatch(base_policy):
    member = Member(member_id="EMP001", name="John Doe", join_date=date(2024, 1, 1), policy_id="POL_OTHER", is_active=True)
    ctx = AdjudicationContext(
        claim_id="CLM001",
        member=member,
        claim_amount=1000.0,
        treatment_date=date(2024, 6, 1),
        extracted_data=ExtractedData(diagnosis="Viral fever"),
    )
    result = run_eligibility_module(ctx, base_policy)
    assert not result.passed
    assert result.status == "FAIL"
    assert "MEMBER_NOT_COVERED" in result.rejection_reasons

def test_initial_waiting_period(base_policy):
    member = Member(member_id="EMP001", name="John Doe", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE", is_active=True)
    # Treatment date is Jan 15, policy effective date is Jan 1 (initial waiting is 30 days)
    ctx = AdjudicationContext(
        claim_id="CLM001",
        member=member,
        claim_amount=1000.0,
        treatment_date=date(2024, 1, 15),
        extracted_data=ExtractedData(diagnosis="Viral fever"),
    )
    result = run_eligibility_module(ctx, base_policy)
    assert not result.passed
    assert result.status == "FAIL"
    assert "WAITING_PERIOD" in result.rejection_reasons
    assert result.waiting_period_end_date == date(2024, 1, 31)

def test_specific_ailment_waiting_period_diabetes(base_policy):
    # Member joined on Jan 1, treatment on Feb 1 (31 days since join, diabetes waiting is 90 days)
    member = Member(member_id="EMP001", name="John Doe", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE", is_active=True)
    ctx = AdjudicationContext(
        claim_id="CLM001",
        member=member,
        claim_amount=1000.0,
        treatment_date=date(2024, 2, 1),
        extracted_data=ExtractedData(diagnosis="Type 2 Diabetes mellitus"),
    )
    result = run_eligibility_module(ctx, base_policy)
    assert not result.passed
    assert result.status == "FAIL"
    assert "WAITING_PERIOD" in result.rejection_reasons
    assert result.waiting_period_end_date == date(2024, 3, 31) # 90 days after Jan 1

def test_specific_ailment_waiting_period_joint_replacement(base_policy):
    # Member joined on Jan 1, 2024, treatment on Jan 1, 2025 (366 days, joint replacement waiting is 730 days)
    member = Member(member_id="EMP001", name="John Doe", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE", is_active=True)
    ctx = AdjudicationContext(
        claim_id="CLM001",
        member=member,
        claim_amount=1000.0,
        treatment_date=date(2025, 1, 1),
        extracted_data=ExtractedData(diagnosis="Osteoarthritis requiring total joint replacement"),
    )
    result = run_eligibility_module(ctx, base_policy)
    assert not result.passed
    assert result.status == "FAIL"
    assert "WAITING_PERIOD" in result.rejection_reasons

def test_eligibility_passed(base_policy):
    member = Member(member_id="EMP001", name="John Doe", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE", is_active=True)
    # Treatment on May 1 (121 days since join, all waiting periods satisfied)
    ctx = AdjudicationContext(
        claim_id="CLM001",
        member=member,
        claim_amount=1000.0,
        treatment_date=date(2024, 5, 1),
        extracted_data=ExtractedData(diagnosis="Type 2 Diabetes"),
    )
    result = run_eligibility_module(ctx, base_policy)
    assert result.passed
    assert result.status == "PASS"
    assert len(result.rejection_reasons) == 0
