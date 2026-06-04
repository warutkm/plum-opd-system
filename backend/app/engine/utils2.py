from app.models.policy import PolicyTerms
from app.models.claim import ClaimCategory

def get_sub_limit(category: str, policy: PolicyTerms) -> float:
    cov = policy.coverage_details
    limits = {
        ClaimCategory.CONSULTATION.value: cov.consultation_fees.sub_limit,
        ClaimCategory.DIAGNOSTIC.value: cov.diagnostic_tests.sub_limit,
        ClaimCategory.PHARMACY.value: cov.pharmacy.sub_limit,
        ClaimCategory.DENTAL.value: cov.dental.sub_limit,
        ClaimCategory.VISION.value: cov.vision.sub_limit,
        ClaimCategory.ALTERNATIVE_MEDICINE.value: cov.alternative_medicine.sub_limit,
    }
    return limits.get(category, cov.annual_limit)

def get_effective_per_claim_limit(category: str, policy: PolicyTerms) -> float:
    base_limit = policy.coverage_details.per_claim_limit
    sub_limit = get_sub_limit(category, policy)
    return min(base_limit, sub_limit)
