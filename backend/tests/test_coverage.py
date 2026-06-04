import pytest
from datetime import date
from app.models.member import Member
from app.models.policy import PolicyTerms
from app.schemas.claim_schema import AdjudicationContext, ExtractedData
from app.engine.coverage import run_coverage_module


def test_diagnosis_exclusion_weight_loss(base_policy):
    member = Member(member_id="EMP001", name="John Doe", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE")
    ctx = AdjudicationContext(
        claim_id="CLM001",
        member=member,
        claim_amount=5000.0,
        treatment_date="2024-06-01",
        extracted_data=ExtractedData(
            diagnosis="Obesity and weight management",
            procedures=["Bariatric consultation and diet plan"],
        ),
        bill_items={"consultation_fee": 2000, "diet_plan": 3000},
    )
    result = run_coverage_module(ctx, base_policy)
    assert not result.passed
    assert result.status == "FAIL"
    assert "SERVICE_NOT_COVERED" in result.rejection_reasons

def test_pre_auth_required_missing(base_policy):
    member = Member(member_id="EMP001", name="John Doe", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE")
    ctx = AdjudicationContext(
        claim_id="CLM001",
        member=member,
        claim_amount=15000.0,
        treatment_date="2024-06-01",
        extracted_data=ExtractedData(
            diagnosis="Lumbar disc herniation",
            tests=["MRI Lumbar Spine"],
        ),
        bill_items={"mri_scan": 15000},
        has_pre_authorization=False,
    )
    result = run_coverage_module(ctx, base_policy)
    assert not result.passed
    assert result.status == "FAIL"
    assert "PRE_AUTH_MISSING" in result.rejection_reasons

def test_dental_cosmetic_exclusion(base_policy):
    member = Member(member_id="EMP001", name="John Doe", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE")
    ctx = AdjudicationContext(
        claim_id="CLM001",
        member=member,
        claim_amount=5000.0,
        treatment_date="2024-06-01",
        extracted_data=ExtractedData(
            diagnosis="Tooth decay",
            procedures=["Teeth whitening"],
        ),
        bill_items={"teeth_whitening": 5000},
    )
    result = run_coverage_module(ctx, base_policy)
    assert not result.passed
    assert result.status == "FAIL"
    assert "SERVICE_NOT_COVERED" in result.rejection_reasons

def test_lasik_exclusion(base_policy):
    member = Member(member_id="EMP001", name="John Doe", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE")
    ctx = AdjudicationContext(
        claim_id="CLM001",
        member=member,
        claim_amount=8000.0,
        treatment_date="2024-06-01",
        extracted_data=ExtractedData(
            diagnosis="Myopia",
            procedures=["LASIK eye surgery"],
        ),
        bill_items={"lasik_surgery": 8000},
    )
    result = run_coverage_module(ctx, base_policy)
    assert not result.passed
    assert result.status == "FAIL"
    assert "SERVICE_NOT_COVERED" in result.rejection_reasons

def test_partial_coverage_mixed_items(base_policy):
    member = Member(member_id="EMP001", name="John Doe", join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE")
    ctx = AdjudicationContext(
        claim_id="CLM001",
        member=member,
        claim_amount=12000.0,
        treatment_date="2024-06-01",
        extracted_data=ExtractedData(
            diagnosis="Tooth decay requiring root canal",
            procedures=["Root canal treatment", "Teeth whitening"],
        ),
        bill_items={"root_canal": 8000, "teeth_whitening": 4000},
    )
    result = run_coverage_module(ctx, base_policy)
    assert result.passed
    assert result.status == "PARTIAL"
    assert len(result.covered_items) == 1
    assert len(result.excluded_items) == 1
    assert result.covered_items[0].item == "Root canal treatment"
    assert result.excluded_items[0].item == "Teeth whitening"
