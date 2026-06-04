from datetime import date, timedelta
from app.models.policy import PolicyTerms
from app.schemas.claim_schema import AdjudicationContext
from app.schemas.decision_schema import EligibilityResult

def run_eligibility_module(ctx: AdjudicationContext, policy: PolicyTerms) -> EligibilityResult:
    result = EligibilityResult()

    if not ctx.member.is_active:
        result.status = "FAIL"
        result.policy_active = False
        result.rejection_reasons.append("POLICY_INACTIVE")
        result.details["message"] = "Member policy status is inactive"
        return result
    result.policy_active = True

    if ctx.member.policy_id != policy.policy_id:
        result.status = "FAIL"
        result.member_covered = False
        result.rejection_reasons.append("MEMBER_NOT_COVERED")
        result.details["message"] = f"Member is not covered under policy {policy.policy_id}"
        return result
    result.member_covered = True

    eff_date = date.fromisoformat(policy.effective_date)
    days_since_effective = (ctx.treatment_date - eff_date).days
    
    initial_wait = policy.waiting_periods.initial_waiting
    if days_since_effective < initial_wait:
        eligible = eff_date + timedelta(days=initial_wait)
        result.status = "FAIL"
        result.waiting_period_satisfied = False
        result.waiting_period_end_date = eligible
        result.rejection_reasons.append("WAITING_PERIOD")
        result.details["message"] = f"Initial {initial_wait}-day waiting period not met. Eligible from {eligible.isoformat()}"
        return result

    if ctx.extracted_data.diagnosis:
        diag = ctx.extracted_data.diagnosis.lower()
        specific = policy.waiting_periods.specific_ailments
        
        check_ailments = {
            "diabetes": specific.diabetes,
            "hypertension": specific.hypertension,
            "joint replacement": specific.joint_replacement,
        }
        
        for ailment, wait_days in check_ailments.items():
            if ailment in diag:
                days_since_join = (ctx.treatment_date - ctx.member.join_date).days
                if days_since_join < wait_days:
                    eligible = ctx.member.join_date + timedelta(days=wait_days)
                    result.status = "FAIL"
                    result.waiting_period_satisfied = False
                    result.waiting_period_end_date = eligible
                    result.rejection_reasons.append("WAITING_PERIOD")
                    result.details["message"] = f"{ailment.title()} has {wait_days}-day waiting period. Eligible from {eligible.isoformat()}"
                    return result

    result.passed = True
    result.status = "PASS"
    result.waiting_period_satisfied = True
    return result