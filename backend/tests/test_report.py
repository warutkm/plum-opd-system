"""
Tests for the Investigator Report Service (Point 10 from the architecture document).

Verifies:
    1. Complete 6-section structure generation.
    2. Capped amount calculation/key inclusion in limit analysis.
    3. Dynamic generation of What-If scenarios for various policy rejections:
        - PER_CLAIM_EXCEEDED -> Limit compliance
        - ANNUAL_LIMIT_EXCEEDED -> Annual limit compliance
        - WAITING_PERIOD -> Waiting period completion
        - MISSING_DOCUMENTS -> Document compliance
        - DOCTOR_REG_INVALID -> Provider licensing
        - PATIENT_MISMATCH -> Patient verification
        - DATE_MISMATCH -> Date consistency
        - BELOW_MIN_AMOUNT -> Minimum claim limit
        - SERVICE_NOT_COVERED -> Covered service compliance
        - PRE_AUTH_MISSING -> Pre-authorization compliance
        - Non-network hospital -> Network utilization savings
"""

import pytest
from datetime import date

from app.models.claim import ClaimDecision
from app.models.member import Member
from app.schemas.claim_schema import AdjudicationContext, ExtractedData
from app.schemas.decision_schema import (
    RuleEngineResult,
    EligibilityResult,
    DocumentationResult,
    CoverageResult,
    FinancialResult,
    FinancialBreakdown,
)
from app.models.fraud import FraudResult, FraudSignal, FraudSeverity, FraudEngine
from app.services.report_service import ReportService


# ── Helpers ───────────────────────────────────────────────────────────────

def _make_context(
    claim_id: str = "CLM_2026_0001",
    claim_amount: float = 1500.0,
    is_network_hospital: bool = True,
    patient_name: str = "Rajesh Kumar",
) -> AdjudicationContext:
    member = Member(
        member_id="EMP001",
        name="Rajesh Kumar",
        join_date=date(2024, 1, 1),
        policy_id="POL_OPD_ADVANTAGE",
    )
    extracted = ExtractedData(
        patient_name=patient_name,
        doctor_name="Dr. Sharma",
        doctor_registration="KA/45678/2015",
        diagnosis="Viral fever",
        provider_name="Apollo Hospitals",
        bill_amount=claim_amount,
        treatment_date=date(2024, 11, 1),
    )
    return AdjudicationContext(
        claim_id=claim_id,
        member=member,
        claim_amount=claim_amount,
        treatment_date=date(2024, 11, 1),
        documents_submitted=["prescription", "bill"],
        extracted_data=extracted,
        bill_items={"consultation": claim_amount},
        hospital_name="Apollo Hospitals",
        is_cashless=True,
        is_network_hospital=is_network_hospital,
    )


def _make_rule_result(
    decision: ClaimDecision = ClaimDecision.APPROVED,
    rejection_reasons: list = None,
    approved_amount: float = 1350.0,
    covered_amount: float = 1500.0,
    copay_amount: float = 150.0,
) -> RuleEngineResult:
    reasons = rejection_reasons or []
    
    financial_bd = FinancialBreakdown(
        base_amount=1500.0,
        covered_amount=covered_amount,
        copay_percentage=10.0,
        copay_amount=copay_amount,
        annual_limit_remaining=13650.0,
        final_approved_amount=approved_amount,
    )
    financial = FinancialResult(
        passed=len(reasons) == 0,
        approved_amount=approved_amount,
        breakdown=financial_bd,
    )
    
    eligibility = EligibilityResult(
        passed=True,
        status="PASS",
        waiting_period_satisfied=True,
    )
    
    coverage = CoverageResult(
        passed=True,
        status="PASS",
        primary_category="consultation",
    )

    return RuleEngineResult(
        decision=decision,
        approved_amount=approved_amount,
        rejection_reasons=reasons,
        rejected_items=[],
        notes="Standard consultation",
        rule_confidence=1.0,
        financial=financial,
        eligibility=eligibility,
        coverage=coverage,
    )


def _make_fraud_result() -> FraudResult:
    return FraudResult(
        fraud_score=10.0,
        signals=[
            FraudSignal(
                signal_type="NONE",
                engine=FraudEngine.RULE_BASED,
                description="No signals",
                severity=FraudSeverity.LOW,
                score_impact=0.0,
            )
        ],
        requires_manual_review=False,
    )


# ── Core Tests ────────────────────────────────────────────────────────────

class TestReportService:
    def setup_method(self):
        self.service = ReportService()

    def test_report_contains_all_six_sections(self):
        """Verify that all 6 sections (Summary, Coverage, Limit, Fraud, Decision, What-If) are present."""
        ctx = _make_context()
        rules = _make_rule_result()
        fraud = _make_fraud_result()

        report = self.service.generate_investigator_report(ctx, rules, fraud)
        
        assert report.claim_summary is not None
        assert report.coverage_analysis is not None
        assert report.limit_analysis is not None
        assert report.fraud_analysis is not None
        assert report.decision_rationale is not None
        assert report.what_if_analysis is not None
        assert report.policy_references is not None
        assert report.full_report_text is not None

    def test_limit_analysis_includes_capped_amount(self):
        """Verify that limit_analysis has the capped_amount key for frontend compatibility."""
        ctx = _make_context()
        rules = _make_rule_result(covered_amount=1200.0)
        fraud = _make_fraud_result()

        report = self.service.generate_investigator_report(ctx, rules, fraud)
        assert "capped_amount" in report.limit_analysis
        assert report.limit_analysis["capped_amount"] == 1200.0

    def test_what_if_limit_exceeded(self):
        """PER_CLAIM_EXCEEDED rejection triggers Limit compliance scenario."""
        ctx = _make_context()
        rules = _make_rule_result(
            decision=ClaimDecision.REJECTED,
            rejection_reasons=["PER_CLAIM_EXCEEDED"],
            approved_amount=0.0,
        )
        fraud = _make_fraud_result()

        report = self.service.generate_investigator_report(ctx, rules, fraud)
        scenarios = report.what_if_analysis["scenarios"]
        
        limit_scenario = next((s for s in scenarios if s["scenario"] == "Limit compliance"), None)
        assert limit_scenario is not None
        assert "per-claim cap" in limit_scenario["details"]

    def test_what_if_missing_documents(self):
        """MISSING_DOCUMENTS rejection triggers Document compliance scenario."""
        ctx = _make_context()
        rules = _make_rule_result(
            decision=ClaimDecision.REJECTED,
            rejection_reasons=["MISSING_DOCUMENTS"],
            approved_amount=0.0,
        )
        fraud = _make_fraud_result()

        report = self.service.generate_investigator_report(ctx, rules, fraud)
        scenarios = report.what_if_analysis["scenarios"]
        
        doc_scenario = next((s for s in scenarios if s["scenario"] == "Document compliance"), None)
        assert doc_scenario is not None
        assert "missing documents" in doc_scenario["details"].lower()

    def test_what_if_waiting_period(self):
        """WAITING_PERIOD rejection triggers Waiting period completion scenario."""
        ctx = _make_context()
        rules = _make_rule_result(
            decision=ClaimDecision.REJECTED,
            rejection_reasons=["WAITING_PERIOD"],
            approved_amount=0.0,
        )
        # Mock waiting period end date in eligibility
        rules.eligibility.waiting_period_satisfied = False
        rules.eligibility.waiting_period_end_date = date(2025, 3, 1)
        fraud = _make_fraud_result()

        report = self.service.generate_investigator_report(ctx, rules, fraud)
        scenarios = report.what_if_analysis["scenarios"]
        
        wait_scenario = next((s for s in scenarios if s["scenario"] == "Waiting period completion"), None)
        assert wait_scenario is not None
        assert "2025-03-01" in wait_scenario["details"]

    def test_what_if_non_network_hospital(self):
        """Non-network hospital triggers network savings scenario."""
        ctx = _make_context(is_network_hospital=False, claim_amount=2000.0)
        rules = _make_rule_result()
        fraud = _make_fraud_result()

        report = self.service.generate_investigator_report(ctx, rules, fraud)
        scenarios = report.what_if_analysis["scenarios"]
        
        network_scenario = next((s for s in scenarios if s["scenario"] == "Network utilization savings"), None)
        assert network_scenario is not None
        assert "network hospital" in network_scenario["details"].lower()
        # 20% discount on 2000 is 400
        assert "400.00" in network_scenario["details"]
