from typing import List, Optional
import time

from app.models.policy import PolicyTerms
from app.models.claim import ClaimDecision
from app.models.audit import AuditTraceEntry
from app.schemas.claim_schema import AdjudicationContext
from app.schemas.decision_schema import RuleEngineResult

from app.engine.eligibility import run_eligibility_module
from app.engine.documentation import run_documentation_module
from app.engine.coverage import run_coverage_module
from app.engine.financial import run_financial_module
from app.engine.partial_approval import run_partial_approval_module

class DeterministicRuleEngine:
    """
    Main orchestrator for the deterministic rule engine.
    Calls Modules A, B, C, D, and E sequentially.
    """

    def __init__(self, policy_terms: PolicyTerms) -> None:
        self.policy = policy_terms

    @staticmethod
    def _trace(step: str, status: str, details: Optional[dict] = None) -> AuditTraceEntry:
        return AuditTraceEntry(step=step, status=status, details=details or {})

    @staticmethod
    def _build_rejected(
        reasons: List[str],
        traces: List[AuditTraceEntry],
        eligibility=None,
        documentation=None,
        coverage=None,
        financial=None,
        notes: str = "",
    ) -> RuleEngineResult:
        traces.append(AuditTraceEntry(
            step="decision",
            status="FAIL",
            details={"decision": "REJECTED", "reasons": reasons},
        ))
        return RuleEngineResult(
            decision=ClaimDecision.REJECTED,
            approved_amount=0.0,
            rejection_reasons=reasons,
            notes=notes,
            rule_confidence=0.98,
            eligibility=eligibility,
            documentation=documentation,
            coverage=coverage,
            financial=financial,
            traces=traces,
        )

    def adjudicate(self, ctx: AdjudicationContext) -> RuleEngineResult:
        traces: List[AuditTraceEntry] = []

        # MODULE A: ELIGIBILITY
        eligibility = run_eligibility_module(ctx, self.policy)
        traces.append(self._trace("module_a_eligibility", eligibility.status, eligibility.details))
        if not eligibility.passed:
            return self._build_rejected(eligibility.rejection_reasons, traces, eligibility=eligibility)

        # MODULE B: DOCUMENTATION
        documentation = run_documentation_module(ctx, self.policy)
        traces.append(self._trace("module_b_documentation", documentation.status, documentation.details))
        if not documentation.passed:
            return self._build_rejected(documentation.rejection_reasons, traces, eligibility=eligibility, documentation=documentation)

        # MODULE C: COVERAGE
        coverage = run_coverage_module(ctx, self.policy)
        traces.append(self._trace("module_c_coverage", coverage.status, coverage.details))
        if not coverage.passed:
            return self._build_rejected(coverage.rejection_reasons, traces, eligibility=eligibility, documentation=documentation, coverage=coverage)

        # MODULE D: FINANCIAL
        financial = run_financial_module(ctx, coverage, self.policy)
        traces.append(self._trace("module_d_financial", financial.status, financial.details))
        if not financial.passed:
            return self._build_rejected(financial.rejection_reasons, traces, eligibility=eligibility, documentation=documentation, coverage=coverage, financial=financial)

        # MODULE E: PARTIAL APPROVAL
        partial = None
        if coverage.has_excluded_items and coverage.has_covered_items:
            partial = run_partial_approval_module(coverage, financial)
            traces.append(self._trace("module_e_partial_approval", partial.status, partial.details))

        # DECISION
        decision = ClaimDecision.PARTIAL if partial else ClaimDecision.APPROVED
        notes = "Claim approved completely" if not partial else "Claim partially approved; some items excluded"
        rejected_items = [it.item for it in coverage.excluded_items] if coverage.excluded_items else []

        traces.append(self._trace("decision", "PASS", {"decision": decision.value, "amount": financial.approved_amount}))

        return RuleEngineResult(
            decision=decision,
            approved_amount=financial.approved_amount,
            rejection_reasons=[],
            rejected_items=rejected_items,
            notes=notes,
            rule_confidence=0.98,
            is_cashless_approved=financial.is_cashless_approved,
            eligibility=eligibility,
            documentation=documentation,
            coverage=coverage,
            financial=financial,
            partial_approval=partial,
            traces=traces,
        )