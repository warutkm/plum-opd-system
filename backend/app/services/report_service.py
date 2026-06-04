from datetime import datetime
from typing import Any, Dict, List, Optional
from app.models.report import InvestigatorReport
from app.schemas.claim_schema import AdjudicationContext
from app.schemas.decision_schema import RuleEngineResult
from app.models.fraud import FraudResult

class ReportService:
    def generate_investigator_report(
        self,
        ctx: AdjudicationContext,
        rule_result: RuleEngineResult,
        fraud_result: FraudResult,
    ) -> InvestigatorReport:
        """
        Generate a comprehensive, dynamic 6-section investigator report
        based on the adjudication context and results.
        """
        # Section 1: Claim Summary
        summary = {
            "claim_id": ctx.claim_id,
            "member_id": ctx.member.member_id,
            "patient_name": ctx.extracted_data.patient_name or ctx.member.name,
            "age": ctx.extracted_data.age or "Unknown",
            "diagnosis": ctx.extracted_data.diagnosis or "Not Specified",
            "provider_name": ctx.extracted_data.provider_name or ctx.hospital_name or "Unknown",
            "treatment_date": ctx.treatment_date.isoformat(),
            "claim_amount": ctx.claim_amount,
            "approved_amount": rule_result.approved_amount,
        }

        # Section 2: Coverage Analysis
        covered_items_list = []
        excluded_items_list = []
        if rule_result.coverage:
            for it in rule_result.coverage.covered_items:
                covered_items_list.append({
                    "item": it.item,
                    "amount": it.amount,
                    "category": it.category or rule_result.coverage.primary_category,
                })
            for it in rule_result.coverage.excluded_items:
                excluded_items_list.append({
                    "item": it.item,
                    "amount": it.amount,
                    "exclusion_reason": it.exclusion_reason or "Excluded service",
                })

        cov_analysis = {
            "primary_category": rule_result.coverage.primary_category if rule_result.coverage else "unknown",
            "covered_items": covered_items_list,
            "excluded_items": excluded_items_list,
            "has_covered_items": rule_result.coverage.has_covered_items if rule_result.coverage else False,
            "has_excluded_items": rule_result.coverage.has_excluded_items if rule_result.coverage else False,
        }

        # Section 3: Limit Analysis
        financial_bd = rule_result.financial.breakdown if rule_result.financial else None
        limit_analysis = {
            "capped_amount": financial_bd.covered_amount if financial_bd else 0.0,
            "per_claim_limit": financial_bd.per_claim_limit_cap if financial_bd else 0.0,
            "category_sub_limit": financial_bd.sub_limit_cap if financial_bd else 0.0,
            "annual_limit_remaining_before": (financial_bd.annual_limit_remaining + rule_result.approved_amount) if financial_bd else 0.0,
            "annual_limit_remaining_after": financial_bd.annual_limit_remaining if financial_bd else 0.0,
            "copay_percentage": financial_bd.copay_percentage if financial_bd else 0.0,
            "copay_amount": financial_bd.copay_amount if financial_bd else 0.0,
            "network_discount_percentage": financial_bd.network_discount_percentage if financial_bd else 0.0,
            "network_discount_amount": financial_bd.network_discount_amount if financial_bd else 0.0,
        }

        # Section 4: Fraud Analysis
        signals_list = []
        for s in fraud_result.signals:
            signals_list.append({
                "signal_type": s.signal_type,
                "engine": s.engine.value,
                "severity": s.severity.value,
                "description": s.description,
                "score_impact": s.score_impact,
            })

        fraud_analysis = {
            "fraud_score": fraud_result.fraud_score,
            "requires_manual_review": fraud_result.requires_manual_review,
            "signals": signals_list,
        }

        # Section 5: Decision Rationale
        decision_rationale = {
            "decision": rule_result.decision.value,
            "rejection_reasons": list(rule_result.rejection_reasons),
            "notes": rule_result.notes,
            "rule_confidence": rule_result.rule_confidence,
        }

        # Section 6: What-If Analysis
        what_if_scenarios = []
        
        # Scenario 1: Rejection due to per-claim limit
        if "PER_CLAIM_EXCEEDED" in rule_result.rejection_reasons:
            what_if_scenarios.append({
                "scenario": "Limit compliance",
                "details": f"If the claim amount were reduced to the per-claim cap of ₹{limit_analysis['per_claim_limit']:,.2f}, the claim would be approved."
            })
            
        # Scenario 2: Rejection due to annual limit
        if "ANNUAL_LIMIT_EXCEEDED" in rule_result.rejection_reasons:
            remaining = limit_analysis['annual_limit_remaining_before']
            what_if_scenarios.append({
                "scenario": "Annual limit compliance",
                "details": f"If the claim amount were below the remaining annual limit of ₹{remaining:,.2f}, it would be approved up to that amount."
            })

        # Scenario 3: Rejection due to inactive policy
        if "POLICY_INACTIVE" in rule_result.rejection_reasons:
            what_if_scenarios.append({
                "scenario": "Policy activation",
                "details": "If the employer's corporate group policy was active on the date of treatment, the claim would be eligible for adjudication."
            })

        # Scenario 4: Member not covered
        if "MEMBER_NOT_COVERED" in rule_result.rejection_reasons:
            what_if_scenarios.append({
                "scenario": "Member coverage",
                "details": f"If patient '{ctx.member.name}' was registered under the company policy, the claim would be covered."
            })

        # Scenario 5: Waiting period
        if "WAITING_PERIOD" in rule_result.rejection_reasons:
            end_date = rule_result.eligibility.waiting_period_end_date if rule_result.eligibility else None
            date_str = end_date.strftime("%Y-%m-%d") if end_date else "the waiting period end date"
            what_if_scenarios.append({
                "scenario": "Waiting period completion",
                "details": f"If the treatment date was after {date_str}, the waiting period would be satisfied and the claim would be eligible for payout."
            })

        # Scenario 6: Rejection due to missing documents
        if "MISSING_DOCUMENTS" in rule_result.rejection_reasons:
            what_if_scenarios.append({
                "scenario": "Document compliance",
                "details": "If the missing documents (e.g., doctor prescription) were submitted, the claim would pass documentation validation."
            })

        # Scenario 7: Invalid doctor registration
        if "DOCTOR_REG_INVALID" in rule_result.rejection_reasons:
            what_if_scenarios.append({
                "scenario": "Provider licensing",
                "details": "If the consultation was conducted by a medical practitioner with a valid, verified registration number, it would be approved."
            })

        # Scenario 8: Patient mismatch
        if "PATIENT_MISMATCH" in rule_result.rejection_reasons:
            what_if_scenarios.append({
                "scenario": "Patient verification",
                "details": f"If the patient name on the bill matched the registered member name '{ctx.member.name}', the claim would pass verification."
            })

        # Scenario 9: Date mismatch
        if "DATE_MISMATCH" in rule_result.rejection_reasons:
            what_if_scenarios.append({
                "scenario": "Date consistency",
                "details": "If the treatment date on the bill matched the date specified on the doctor's prescription, the claim would pass validation."
            })

        # Scenario 10: Below minimum amount
        if "BELOW_MIN_AMOUNT" in rule_result.rejection_reasons:
            what_if_scenarios.append({
                "scenario": "Minimum claim limit",
                "details": "If the total bill amount exceeded the minimum claim threshold of ₹100, the claim would be processed."
            })

        # Scenario 11: Service not covered (obesity, cosmetic, teeth whitening)
        if "SERVICE_NOT_COVERED" in rule_result.rejection_reasons:
            category = cov_analysis["primary_category"].upper()
            what_if_scenarios.append({
                "scenario": "Covered service compliance",
                "details": f"If the treatment was a covered OPD benefit (e.g., general practitioner consultation) rather than an excluded category under the policy terms, the claim would be approved."
            })

        # Scenario 12: Pre-auth missing
        if "PRE_AUTH_MISSING" in rule_result.rejection_reasons:
            what_if_scenarios.append({
                "scenario": "Pre-authorization compliance",
                "details": "If a pre-authorization request was submitted and approved prior to undergoing the diagnostic tests, the claim would be approved."
            })

        # Scenario 13: Non-network hospital utilization
        if not ctx.is_network_hospital:
            potential_saving = ctx.claim_amount * 0.20
            what_if_scenarios.append({
                "scenario": "Network utilization savings",
                "details": f"If the member visited a network hospital, a 20% network discount of ₹{potential_saving:,.2f} would apply, reducing their co-pay."
            })
        else:
            what_if_scenarios.append({
                "scenario": "Network utilization savings",
                "details": "The claim utilized a network hospital, saving 20% on cashless approvals."
            })

        what_if_analysis = {
            "scenarios": what_if_scenarios,
        }

        # Generate markdown text
        rejection_str = f", reasons: {', '.join(rule_result.rejection_reasons)}" if rule_result.rejection_reasons else ""
        md = f"""# Medical Adjudication Investigator Report
Report generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
Claim ID: **{ctx.claim_id}**

---

## 1. Claim Summary
- **Patient Name:** {summary['patient_name']}
- **Member ID:** {summary['member_id']} (Age: {summary['age']})
- **Primary Diagnosis:** {summary['diagnosis']}
- **Provider Name:** {summary['provider_name']}
- **Treatment Date:** {summary['treatment_date']}
- **Claimed Amount:** ₹{summary['claim_amount']:,}
- **Approved Amount:** ₹{summary['approved_amount']:,}

## 2. Coverage Analysis
- **Primary Benefit Category:** {cov_analysis['primary_category'].upper()}
- **Covered Items ({len(cov_analysis['covered_items'])}):**
"""
        for item in cov_analysis['covered_items']:
            md += f"  - {item['item']}: ₹{item['amount']:,} ({item['category']})\n"
        if not cov_analysis['covered_items']:
            md += "  - None\n"

        md += "\n- **Excluded/Rejected Items ({len(cov_analysis['excluded_items'])}):**\n"
        for item in cov_analysis['excluded_items']:
            md += f"  - {item['item']}: ₹{item['amount']:,} (Reason: {item['exclusion_reason']})\n"
        if not cov_analysis['excluded_items']:
            md += "  - None\n"

        md += f"""
## 3. Financial Limits Analysis
- **Per-Claim Limit Cap:** ₹{limit_analysis['per_claim_limit']:,}
- **Category Sub-Limit Cap:** ₹{limit_analysis['category_sub_limit']:,}
- **Annual Limit Remaining (Before):** ₹{limit_analysis['annual_limit_remaining_before']:,}
- **Annual Limit Remaining (After):** ₹{limit_analysis['annual_limit_remaining_after']:,}
- **Applied Co-Pay:** {limit_analysis['copay_percentage']}% (₹{limit_analysis['copay_amount']:,})
- **Applied Network Discount:** {limit_analysis['network_discount_percentage']}% (₹{limit_analysis['network_discount_amount']:,})

## 4. Fraud Risk Assessment
- **Aggregated Fraud Risk Score:** {fraud_analysis['fraud_score']}/100
- **Manual Review Required:** {"Yes" if fraud_analysis['requires_manual_review'] else "No"}
- **Fraud Signals Triggered ({len(fraud_analysis['signals'])}):**
"""
        for sig in fraud_analysis['signals']:
            md += f"  - **[{sig['severity']}]** {sig['signal_type']} (Engine: {sig['engine']}): {sig['description']} (Impact: +{sig['score_impact']})\n"
        if not fraud_analysis['signals']:
            md += "  - None\n"

        md += f"""
## 5. Decision & Rationale
- **Final Decision:** **{decision_rationale['decision']}**{rejection_str}
- **Rules Engine Confidence:** {decision_rationale['rule_confidence']}
- **Adjuster Notes:** {decision_rationale['notes'] or 'None'}

## 6. What-If Analysis
"""
        for idx, scenario in enumerate(what_if_scenarios):
            md += f"### Scenario {idx+1}: {scenario['scenario']}\n{scenario['details']}\n\n"

        policy_references = [
            {"section": "OPD Benefit Coverage Guidelines", "rules": ["Section A: Eligibility", "Section B: Sub-limits"]},
            {"section": "Preferred Provider Network Terms", "rules": ["20% Cashless Discount"]}
        ]

        return InvestigatorReport(
            claim_summary=summary,
            coverage_analysis=cov_analysis,
            limit_analysis=limit_analysis,
            fraud_analysis=fraud_analysis,
            decision_rationale=decision_rationale,
            what_if_analysis=what_if_analysis,
            policy_references=policy_references,
            full_report_text=md.strip(),
        )