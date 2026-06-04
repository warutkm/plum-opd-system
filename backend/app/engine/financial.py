from app.models.policy import PolicyTerms
from app.schemas.claim_schema import AdjudicationContext
from app.schemas.decision_schema import FinancialResult, FinancialBreakdown, CoverageResult
from app.engine.utils import get_copay_percentage, is_network_hospital
from app.engine.utils2 import get_sub_limit, get_effective_per_claim_limit

def run_financial_module(ctx: AdjudicationContext, coverage: CoverageResult, policy: PolicyTerms) -> FinancialResult:
    result = FinancialResult()
    breakdown = FinancialBreakdown()
    cov = policy.coverage_details
    cat = coverage.primary_category

    if coverage.has_excluded_items and coverage.has_covered_items:
        base = sum(it.amount for it in coverage.covered_items)
    else:
        base = ctx.claim_amount
    breakdown.base_amount = base

    per_claim_cap = get_effective_per_claim_limit(cat, policy)
    breakdown.per_claim_limit_cap = per_claim_cap

    if not coverage.has_excluded_items and ctx.claim_amount > per_claim_cap:
        result.status = "FAIL"
        result.rejection_reasons.append("PER_CLAIM_EXCEEDED")
        result.details["message"] = f"Claim amount {ctx.claim_amount} exceeds per-claim limit of {per_claim_cap}"
        result.breakdown = breakdown
        return result

    if coverage.covered_items:
        total_covered = 0.0
        for item in coverage.covered_items:
            item_cat = item.category or cat
            item_sub_limit = get_sub_limit(item_cat, policy)
            capped_amt = min(item.amount, item_sub_limit)
            total_covered += capped_amt
    else:
        total_covered = min(base, get_sub_limit(cat, policy))

    # For partial approvals (some items excluded), covered items are already
    # individually capped by their sub-limits — no extra per-claim cap.
    # For full claims, the per-claim rejection (above) already guards the limit.
    effective = total_covered
    breakdown.covered_amount = effective

    sub_limit = get_sub_limit(cat, policy)
    breakdown.sub_limit_cap = sub_limit

    annual_remaining = cov.annual_limit - ctx.ytd_approved_total
    breakdown.annual_limit_remaining = max(0.0, annual_remaining)
    if annual_remaining <= 0:
        result.status = "FAIL"
        result.rejection_reasons.append("ANNUAL_LIMIT_EXCEEDED")
        result.details["message"] = f"Annual limit exhausted (YTD approved: {ctx.ytd_approved_total})"
        result.breakdown = breakdown
        return result
    if effective > annual_remaining:
        effective = annual_remaining

    is_network = ctx.is_network_hospital or is_network_hospital(ctx.hospital_name, policy)

    if is_network:
        discount_pct = cov.consultation_fees.network_discount
        discount_amt = round(effective * discount_pct / 100, 2)
        effective = round(effective - discount_amt, 2)
        breakdown.network_discount_percentage = discount_pct
        breakdown.network_discount_amount = discount_amt
    else:
        copay_pct = get_copay_percentage(cat, policy)
        if copay_pct > 0:
            copay_amt = round(effective * copay_pct / 100, 2)
            effective = round(effective - copay_amt, 2)
            breakdown.copay_percentage = copay_pct
            breakdown.copay_amount = copay_amt

    cashless_approved = False
    if ctx.is_cashless and is_network:
        instant_limit = policy.cashless_facilities.instant_approval_limit
        if effective <= instant_limit:
            cashless_approved = True

    breakdown.final_approved_amount = round(effective, 2)
    result.approved_amount = round(effective, 2)
    result.is_cashless_approved = cashless_approved
    result.breakdown = breakdown
    result.passed = True
    result.status = "PASS"
    result.details = {
        "base_amount": breakdown.base_amount,
        "per_claim_limit": per_claim_cap,
        "sub_limit": sub_limit,
        "copay": breakdown.copay_amount,
        "network_discount": breakdown.network_discount_amount,
        "approved_amount": result.approved_amount,
    }
    return result