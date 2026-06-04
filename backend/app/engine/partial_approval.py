from app.schemas.decision_schema import CoverageResult, FinancialResult, PartialApprovalResult

def run_partial_approval_module(coverage: CoverageResult, financial: FinancialResult) -> PartialApprovalResult:
    result = PartialApprovalResult()
    result.approved_items = [it for it in coverage.covered_items if it.is_covered]
    result.rejected_items = coverage.excluded_items
    
    result.approved_amount = financial.approved_amount
    result.rejected_amount = sum(it.amount for it in coverage.excluded_items)
    
    result.passed = True
    result.status = "PARTIAL"
    return result