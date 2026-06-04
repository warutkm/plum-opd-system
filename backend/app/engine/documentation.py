from app.models.policy import PolicyTerms
from app.schemas.claim_schema import AdjudicationContext
from app.schemas.decision_schema import DocumentationResult
from app.utils.validators import validate_doctor_registration

def run_documentation_module(ctx: AdjudicationContext, policy: PolicyTerms) -> DocumentationResult:
    result = DocumentationResult()
    docs = [d.lower() for d in ctx.documents_submitted]

    has_prescription = "prescription" in docs
    has_bill = "bill" in docs or "medical_bill" in docs

    result.has_prescription = has_prescription
    result.has_bill = has_bill

    if not has_prescription:
        result.status = "FAIL"
        result.rejection_reasons.append("MISSING_DOCUMENTS")
        result.details["message"] = "Prescription from registered doctor is required"
        result.details["missing"] = "prescription"
        return result

    if not has_bill:
        result.status = "FAIL"
        result.rejection_reasons.append("MISSING_DOCUMENTS")
        result.details["message"] = "Medical bill / invoice is required"
        result.details["missing"] = "bill"
        return result

    doc_reg = (ctx.extracted_data.doctor_registration or "").strip()
    if doc_reg:
        result.doctor_reg_valid = validate_doctor_registration(doc_reg)
        if not result.doctor_reg_valid:
            result.status = "FAIL"
            result.rejection_reasons.append("DOCTOR_REG_INVALID")
            result.details["message"] = f"Doctor registration '{doc_reg}' does not match expected format"
            return result
    else:
        result.doctor_reg_valid = False
        result.status = "FAIL"
        result.rejection_reasons.append("DOCTOR_REG_INVALID")
        result.details["message"] = "Doctor registration number is missing"
        return result

    member_name = ctx.member.name.lower().strip()
    patient_name = (ctx.extracted_data.patient_name or "").lower().strip()
    if patient_name and member_name:
        member_parts = set(member_name.split())
        patient_parts = set(patient_name.split())
        if not member_parts.intersection(patient_parts):
            result.patient_match = False
            result.status = "FAIL"
            result.rejection_reasons.append("PATIENT_MISMATCH")
            result.details["message"] = f"Patient name '{patient_name}' does not match member name '{member_name}'"
            return result

    extracted_date = ctx.extracted_data.treatment_date
    if extracted_date and extracted_date != ctx.treatment_date:
        result.date_consistent = False
        result.status = "FAIL"
        result.rejection_reasons.append("DATE_MISMATCH")
        result.details["message"] = f"Treatment date in documents ({extracted_date}) does not match claimed date ({ctx.treatment_date})"
        return result

    min_amount = policy.claim_requirements.minimum_claim_amount
    if ctx.claim_amount < min_amount:
        result.status = "FAIL"
        result.rejection_reasons.append("BELOW_MIN_AMOUNT")
        result.details["message"] = f"Claim amount {ctx.claim_amount} is below minimum {min_amount}"
        return result

    result.passed = True
    result.status = "PASS"
    return result