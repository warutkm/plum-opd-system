from typing import List
from app.models.policy import PolicyTerms
from app.schemas.claim_schema import AdjudicationContext
from app.schemas.decision_schema import CoverageResult, CoverageItem
from app.engine.utils import (
    determine_category,
    is_excluded_diagnosis,
    has_any_covered_items,
    requires_pre_auth,
    match_procedures_to_amounts,
    is_cosmetic_dental,
    is_excluded_procedure,
    get_exclusion_reason,
    _BILL_KEY_CATEGORY
)

def run_coverage_module(ctx: AdjudicationContext, policy: PolicyTerms) -> CoverageResult:
    result = CoverageResult()
    diagnosis = (ctx.extracted_data.diagnosis or "").lower()
    procedures = ctx.extracted_data.procedures
    tests = ctx.extracted_data.tests
    bill_items = ctx.bill_items or ctx.extracted_data.bill_items

    primary_cat = determine_category(ctx)
    result.primary_category = primary_cat

    excluded, exclusion_name = is_excluded_diagnosis(diagnosis, [p.lower() for p in procedures])
    if excluded and not has_any_covered_items(procedures, bill_items, primary_cat, policy):
        result.status = "FAIL"
        result.rejection_reasons.append("SERVICE_NOT_COVERED")
        result.details["message"] = f"{exclusion_name} are excluded from coverage"
        result.details["exclusion_matched"] = exclusion_name
        return result

    for test in tests:
        if requires_pre_auth(test, policy) and not ctx.has_pre_authorization:
            result.status = "FAIL"
            result.pre_auth_required = True
            result.pre_auth_satisfied = False
            result.rejection_reasons.append("PRE_AUTH_MISSING")
            result.details["message"] = f"{test} requires pre-authorization"
            return result

    for proc in procedures:
        if requires_pre_auth(proc, policy) and not ctx.has_pre_authorization:
            result.status = "FAIL"
            result.pre_auth_required = True
            result.pre_auth_satisfied = False
            result.rejection_reasons.append("PRE_AUTH_MISSING")
            result.details["message"] = f"{proc} requires pre-authorization"
            return result

    covered_items: List[CoverageItem] = []
    excluded_items: List[CoverageItem] = []

    if procedures and bill_items:
        proc_amounts, used_keys = match_procedures_to_amounts(procedures, bill_items)
        for proc, amount in proc_amounts:
            if is_cosmetic_dental(proc, policy):
                excluded_items.append(CoverageItem(item=proc, amount=amount, category="dental", is_covered=False, exclusion_reason="Cosmetic procedure excluded"))
            elif is_excluded_procedure(proc):
                exclusion = get_exclusion_reason(proc)
                excluded_items.append(CoverageItem(item=proc, amount=amount, category=primary_cat, is_covered=False, exclusion_reason=exclusion))
            else:
                covered_items.append(CoverageItem(item=proc, amount=amount, category=primary_cat, is_covered=True))
        
        for key, amount in bill_items.items():
            if key not in used_keys:
                item_cat = _BILL_KEY_CATEGORY.get(key, primary_cat)
                if item_cat == "excluded":
                    excluded_items.append(CoverageItem(item=key.replace("_", " ").title(), amount=amount, category=item_cat, is_covered=False, exclusion_reason="Excluded service"))
                else:
                    covered_items.append(CoverageItem(item=key.replace("_", " ").title(), amount=amount, category=item_cat, is_covered=True))
    elif bill_items and not procedures:
        for key, amount in bill_items.items():
            item_cat = _BILL_KEY_CATEGORY.get(key, primary_cat)
            if item_cat == "excluded":
                excluded_items.append(CoverageItem(item=key.replace("_", " ").title(), amount=amount, category=item_cat, is_covered=False, exclusion_reason="Excluded service"))
            else:
                covered_items.append(CoverageItem(item=key.replace("_", " ").title(), amount=amount, category=item_cat, is_covered=True))

    coverage = policy.coverage_details
    if primary_cat == "dental" and not coverage.dental.covered:
        result.status = "FAIL"
        result.rejection_reasons.append("SERVICE_NOT_COVERED")
        result.details["message"] = "Dental services are not covered"
        return result
    if primary_cat == "vision" and not coverage.vision.covered:
        result.status = "FAIL"
        result.rejection_reasons.append("SERVICE_NOT_COVERED")
        return result
    if primary_cat == "alternative_medicine" and not coverage.alternative_medicine.covered:
        result.status = "FAIL"
        result.rejection_reasons.append("SERVICE_NOT_COVERED")
        return result

    if primary_cat == "vision":
        for proc in procedures:
            if "lasik" in proc.lower():
                result.status = "FAIL"
                result.rejection_reasons.append("SERVICE_NOT_COVERED")
                result.details["message"] = "LASIK surgery is not covered"
                return result

    result.covered_items = covered_items
    result.excluded_items = excluded_items
    result.has_covered_items = len(covered_items) > 0 or (not covered_items and not excluded_items)
    result.has_excluded_items = len(excluded_items) > 0

    if excluded_items and not covered_items and not result.has_covered_items:
        result.status = "FAIL"
        result.rejection_reasons.append("SERVICE_NOT_COVERED")
        result.details["message"] = "All items in claim are excluded"
        return result

    result.passed = True
    result.status = "PASS" if not excluded_items else "PARTIAL"
    return result