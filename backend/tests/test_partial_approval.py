import pytest
from app.schemas.decision_schema import CoverageResult, CoverageItem, FinancialResult
from app.engine.partial_approval import run_partial_approval_module

def test_partial_approval_split():
    cov_result = CoverageResult(
        passed=True,
        status="PARTIAL",
        primary_category="dental",
        covered_items=[
            CoverageItem(item="Root canal treatment", amount=8000.0, category="dental", is_covered=True)
        ],
        excluded_items=[
            CoverageItem(item="Teeth whitening", amount=4000.0, category="dental", is_covered=False, exclusion_reason="Cosmetic procedure excluded")
        ],
        has_covered_items=True,
        has_excluded_items=True
    )
    
    fin_result = FinancialResult(
        passed=True,
        status="PASS",
        approved_amount=8000.0
    )
    
    result = run_partial_approval_module(cov_result, fin_result)
    assert result.passed
    assert result.status == "PARTIAL"
    assert len(result.approved_items) == 1
    assert len(result.rejected_items) == 1
    assert result.approved_amount == 8000.0
    assert result.rejected_amount == 4000.0
    assert result.approved_items[0].item == "Root canal treatment"
    assert result.rejected_items[0].item == "Teeth whitening"
