import pytest
from datetime import date
from app.models.member import Member
from app.models.policy import PolicyTerms
from app.schemas.claim_schema import AdjudicationContext, ExtractedData
from app.schemas.decision_schema import CoverageResult, CoverageItem
from app.engine.financial import run_financial_module


def test_per_claim_limit_exceeded(base_policy):
    member = Member(member_id="EMP001", name="John Doe", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE")
    ctx = AdjudicationContext(
        claim_id="CLM001",
        member=member,
        claim_amount=7500.0,  # exceeds default 5000 limit
        treatment_date="2024-06-01",
        extracted_data=ExtractedData(diagnosis="Gastroenteritis"),
        bill_items={"consultation_fee": 2000, "medicines": 5500},
    )
    # Reconstruct a fully covered coverage result
    cov_result = CoverageResult(
        passed=True,
        status="PASS",
        primary_category="consultation",
        covered_items=[
            CoverageItem(item="Consultation", amount=2000, category="consultation", is_covered=True),
            CoverageItem(item="Medicines", amount=5500, category="pharmacy", is_covered=True)
        ]
    )
    result = run_financial_module(ctx, cov_result, base_policy)
    assert not result.passed
    assert result.status == "FAIL"
    assert "PER_CLAIM_EXCEEDED" in result.rejection_reasons

def test_annual_limit_exhausted(base_policy):
    member = Member(member_id="EMP001", name="John Doe", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE")
    ctx = AdjudicationContext(
        claim_id="CLM001",
        member=member,
        claim_amount=3000.0,
        treatment_date="2024-06-01",
        extracted_data=ExtractedData(diagnosis="Viral fever"),
        ytd_approved_total=15000.0,  # annual limit is 15000
    )
    cov_result = CoverageResult(
        passed=True,
        status="PASS",
        primary_category="consultation",
        covered_items=[
            CoverageItem(item="Consultation", amount=1500, category="consultation", is_covered=True)
        ]
    )
    result = run_financial_module(ctx, cov_result, base_policy)
    assert not result.passed
    assert result.status == "FAIL"
    assert "ANNUAL_LIMIT_EXCEEDED" in result.rejection_reasons

def test_consultation_copay_deducted(base_policy):
    member = Member(member_id="EMP001", name="John Doe", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE")
    ctx = AdjudicationContext(
        claim_id="CLM001",
        member=member,
        claim_amount=1500.0,
        treatment_date="2024-06-01",
        extracted_data=ExtractedData(diagnosis="Viral fever"),
        is_network_hospital=False,  # triggers copay
    )
    cov_result = CoverageResult(
        passed=True,
        status="PASS",
        primary_category="consultation",
        covered_items=[
            CoverageItem(item="Consultation Fee", amount=1000, category="consultation", is_covered=True),
            CoverageItem(item="Diagnostic Tests", amount=500, category="diagnostic", is_covered=True)
        ]
    )
    result = run_financial_module(ctx, cov_result, base_policy)
    assert result.passed
    assert result.status == "PASS"
    # Consultation gets 10% copay (₹1500 total claim * 10% copay = ₹150 copay)
    # Approved amount = 1500 - 150 = 1350
    assert result.approved_amount == 1350.0
    assert result.breakdown.copay_percentage == 10
    assert result.breakdown.copay_amount == 150.0

def test_network_discount_applied(base_policy):
    member = Member(member_id="EMP001", name="John Doe", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE")
    # Treatment at network hospital triggers 20% discount (instead of copay)
    ctx = AdjudicationContext(
        claim_id="CLM001",
        member=member,
        claim_amount=4500.0,
        treatment_date="2024-06-01",
        hospital_name="Apollo Hospitals",
        is_network_hospital=True,
        is_cashless=True,
    )
    cov_result = CoverageResult(
        passed=True,
        status="PASS",
        primary_category="consultation",
        covered_items=[
            CoverageItem(item="Consultation Fee", amount=1500, category="consultation", is_covered=True),
            CoverageItem(item="Medicines", amount=3000, category="pharmacy", is_covered=True)
        ]
    )
    result = run_financial_module(ctx, cov_result, base_policy)
    assert result.passed
    assert result.status == "PASS"
    # 20% discount on 4500 = 900. Net approved = 3600
    assert result.approved_amount == 3600.0
    assert result.breakdown.network_discount_percentage == 20
    assert result.breakdown.network_discount_amount == 900.0
    assert result.is_cashless_approved is True  # 3600 is below cashless instant limit of 5000
