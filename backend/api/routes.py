"""
Plum OPD Claim Adjudication System — API Routes
================================================
Defines endpoints for submitting/uploading claims, checking status,
processing claims directly, and querying the RAG Policy Assistant.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import date, datetime
from typing import Any, Dict, List, Optional

import psycopg2
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor

from app.services.claim_service import ClaimService
from app.rag.generator import Generator
from app.services.report_service import ReportService
from app.models.claim import ClaimDecision, ClaimStatus
from app.models.audit import AuditTraceEntry
from app.models.member import Member
from app.models.policy import PolicyTerms
from app.schemas.claim_schema import AdjudicationContext, ExtractedData
from app.schemas.decision_schema import RuleEngineResult
from app.models.fraud import FraudResult
from app.models.rag import RAGQuery, RAGResponse
from app.models.report import InvestigatorReport
from app.schemas.api_schema import HealthResponse, ReviewAction, ClaimDecisionOutput

logger = logging.getLogger(__name__)


class ProcessClaimRequest(BaseModel):
    """Payload schema for Direct-process claim endpoint."""
    member_id: str
    member_name: Optional[str] = None
    treatment_date: date
    claim_amount: float
    hospital_name: Optional[str] = None
    is_cashless: bool = False
    has_pre_authorization: bool = False
    documents_submitted: List[str] = ["prescription", "bill"]
    extracted_data: ExtractedData = ExtractedData()
    bill_items: Dict[str, float] = {}
    member_join_date: Optional[date] = None
    previous_claims_same_day: int = 0


router = APIRouter(prefix="/api/v1")

# ── Shared In-memory Storage (for local fallback) ────────────────
_claims_db: Dict[str, Dict[str, Any]] = {}
_members_db: Dict[str, Member] = {}

# Seed initial members if they do not exist
def _seed_members_if_empty(policy_id: str):
    if not _members_db:
        members = [
            Member(member_id="EMP001", name="Rajesh Kumar", join_date=date(2024, 1, 1), policy_id=policy_id),
            Member(member_id="EMP002", name="Priya Singh", join_date=date(2024, 1, 1), policy_id=policy_id),
            Member(member_id="EMP003", name="Amit Verma", join_date=date(2024, 1, 1), policy_id=policy_id),
            Member(member_id="EMP004", name="Sneha Reddy", join_date=date(2024, 1, 1), policy_id=policy_id),
            Member(member_id="EMP005", name="Vikram Joshi", join_date=date(2024, 9, 1), policy_id=policy_id),
            Member(member_id="EMP006", name="Kavita Nair", join_date=date(2024, 1, 1), policy_id=policy_id),
            Member(member_id="EMP007", name="Suresh Patil", join_date=date(2024, 1, 1), policy_id=policy_id),
            Member(member_id="EMP008", name="Ravi Menon", join_date=date(2024, 1, 1), policy_id=policy_id),
            Member(member_id="EMP009", name="Anita Desai", join_date=date(2024, 1, 1), policy_id=policy_id),
            Member(member_id="EMP010", name="Deepak Shah", join_date=date(2024, 1, 1), policy_id=policy_id),
        ]
        for m in members:
            _members_db[m.member_id] = m


# ── Dependency Injectors ─────────────────────────────────────────

def get_policy_terms() -> PolicyTerms:
    from main import _policy_terms
    if _policy_terms is None:
        raise HTTPException(
            status_code=503,
            detail="Policy terms configuration not loaded on server.",
        )
    # Seed the members database
    _seed_members_if_empty(_policy_terms.policy_id)
    return _policy_terms


def get_pipeline(policy: PolicyTerms = Depends(get_policy_terms)) -> ClaimService:
    return ClaimService(policy)


def get_rag_assistant() -> Generator:
    return Generator()


# ── Investigator Report Generator ────────────────────────────────

def generate_investigator_report(
    ctx: AdjudicationContext,
    rule_result: RuleEngineResult,
    fraud_result: FraudResult,
) -> InvestigatorReport:
    """Helper to structure the Dynamic Investigator Report."""
    summary = {
        "claim_id": ctx.claim_id,
        "member_id": ctx.member.member_id,
        "patient_name": ctx.extracted_data.patient_name or ctx.member.name,
        "treatment_date": ctx.treatment_date.isoformat(),
        "claim_amount": ctx.claim_amount,
        "approved_amount": rule_result.approved_amount,
    }

    cov_analysis = {
        "primary_category": rule_result.coverage.primary_category if rule_result.coverage else "unknown",
        "covered_items": [
            {"item": it.item, "amount": it.amount, "category": it.category}
            for it in (rule_result.coverage.covered_items if rule_result.coverage else [])
        ],
        "excluded_items": [
            {"item": it.item, "amount": it.amount, "exclusion_reason": it.exclusion_reason}
            for it in (rule_result.coverage.excluded_items if rule_result.coverage else [])
        ],
    }

    limit_analysis = {
        "annual_limit_remaining": rule_result.financial.breakdown.annual_limit_remaining if rule_result.financial and rule_result.financial.breakdown else 0.0,
        "copay_amount": rule_result.financial.breakdown.copay_amount if rule_result.financial and rule_result.financial.breakdown else 0.0,
        "network_discount_amount": rule_result.financial.breakdown.network_discount_amount if rule_result.financial and rule_result.financial.breakdown else 0.0,
        "capped_amount": rule_result.financial.breakdown.covered_amount if rule_result.financial and rule_result.financial.breakdown else 0.0,
    }

    fraud_analysis = {
        "fraud_score": fraud_result.fraud_score,
        "signals": [
            {
                "signal_type": s.signal_type,
                "severity": s.severity.value,
                "description": s.description,
            }
            for s in fraud_result.signals
        ],
    }

    rationale = {
        "decision": rule_result.decision.value,
        "rejection_reasons": rule_result.rejection_reasons,
        "rule_confidence": rule_result.rule_confidence,
    }

    # What-If Cashless Simulation
    what_if = {
        "scenario": "cashless_at_network_hospital",
        "potential_saving": ctx.claim_amount * 0.20 if not ctx.is_network_hospital else 0.0,
        "details": "If treatment is done cashless at a network hospital, a 20% network discount applies, saving co-pays."
    }

    # Markdown formatted text
    md = f"""# Medical Adjudication Report for Claim {ctx.claim_id}
Generated on {datetime.utcnow().isoformat()}

## 1. Claim Summary
- Member: {summary['patient_name']} ({summary['member_id']})
- Treatment Date: {summary['treatment_date']}
- Submitted Amount: ₹{summary['claim_amount']:,}
- Approved Amount: ₹{summary['approved_amount']:,}

## 2. Coverage Verification
- Primary Category: {cov_analysis['primary_category']}
- Covered Items Count: {len(cov_analysis['covered_items'])}
- Excluded Items Count: {len(cov_analysis['excluded_items'])}

## 3. Financial Limits
- Capped Covered Base: ₹{limit_analysis['capped_amount']}
- Copay Deducted: ₹{limit_analysis['copay_amount']}
- Network Discount Applied: ₹{limit_analysis['network_discount_amount']}

## 4. Fraud Risk Assessment
- Aggregated Fraud Score: {fraud_analysis['fraud_score']}/100
- Flags Raised: {len(fraud_analysis['signals'])}

## 5. Decision & Rationale
- Decision: **{rationale['decision']}**
- Reasons: {', '.join(rationale['rejection_reasons']) if rationale['rejection_reasons'] else 'None'}
"""

    return InvestigatorReport(
        claim_summary=summary,
        coverage_analysis=cov_analysis,
        limit_analysis=limit_analysis,
        fraud_analysis=fraud_analysis,
        decision_rationale=rationale,
        what_if_analysis=what_if,
        policy_references=[{"section": "OPD Advantage Coverage Terms"}],
        full_report_text=md.strip(),
    )


# ── API ENDPOINTS ────────────────────────────────────────────────

@router.post(
    "/claims/upload",
    response_model=ClaimDecisionOutput,
    status_code=status.HTTP_201_CREATED,
    tags=["Claims"],
)
async def upload_claim(
    member_id: str = Form(...),
    claim_amount: float = Form(...),
    treatment_date: date = Form(...),
    hospital_name: Optional[str] = Form(None),
    is_cashless: bool = Form(False),
    files: List[UploadFile] = File(...),
    pipeline: ClaimService = Depends(get_pipeline),
):
    """
    Upload and adjudicate a claim with document attachments.
    Parses documents using Gemini and runs the pipeline.
    """
    member = _members_db.get(member_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member record with id {member_id} not found.",
        )

    # Convert uploaded files to bytes for processing
    file_contents: List[Tuple[bytes, str]] = []
    for f in files:
        contents = await f.read()
        file_contents.append((contents, f.content_type or "application/octet-stream"))

    # Process claim through pipeline
    result: ClaimDecisionOutput = pipeline.process_claim(
        member=member,
        claim_amount=claim_amount,
        treatment_date=treatment_date,
        hospital_name=hospital_name,
        is_cashless=is_cashless,
        file_contents=file_contents,
    )

    # Save to local store
    _claims_db[result.claim_id] = {
        "claim_id": result.claim_id,
        "member_id": member_id,
        "claim_amount": claim_amount,
        "approved_amount": result.approved_amount,
        "treatment_date": treatment_date.isoformat(),
        "hospital_name": hospital_name,
        "status": ClaimStatus.DECIDED,
        "decision": result.decision,
        "confidence_score": result.confidence_score,
        "fraud_score": result.fraud_score,
        "trace_summary": [t.model_dump() for t in result.trace_summary],
        "rejection_reasons": result.rejection_reasons,
        "notes": result.notes,
        "created_at": datetime.utcnow().isoformat(),
    }

    return result


@router.get("/claims/{claim_id}/status", tags=["Claims"])
async def get_claim_status(
    claim_id: str,
    policy: PolicyTerms = Depends(get_policy_terms),
):
    """
    Retrieve adjudication status, full Trace Ledger, and Dynamic Investigator Report.
    """
    claim = _claims_db.get(claim_id)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found.",
        )

    # Reconstruct Adjudication Context and results for generating the report
    member = _members_db.get(claim["member_id"])
    ctx = AdjudicationContext(
        claim_id=claim_id,
        member=member,
        claim_amount=claim["claim_amount"],
        treatment_date=date.fromisoformat(claim["treatment_date"]),
        hospital_name=claim["hospital_name"],
    )

    rule_result = RuleEngineResult(
        decision=ClaimDecision(claim["decision"]),
        approved_amount=claim["approved_amount"],
        rejection_reasons=claim["rejection_reasons"],
        notes=claim["notes"],
    )

    fraud_result = FraudResult(
        fraud_score=claim["fraud_score"],
        signals=[],
    )

    report = generate_investigator_report(ctx, rule_result, fraud_result)

    return {
        "claim_id": claim_id,
        "status": claim["status"],
        "decision": claim["decision"],
        "approved_amount": claim["approved_amount"],
        "confidence_score": claim["confidence_score"],
        "fraud_score": claim["fraud_score"],
        "trace_ledger": claim["trace_summary"],
        "investigator_report": report.model_dump(),
    }


@router.post("/claims/process", response_model=ClaimDecisionOutput, tags=["Claims"])
async def process_claim(
    payload: ProcessClaimRequest,
    pipeline: ClaimService = Depends(get_pipeline),
):
    """
    Adjudicate raw JSON claims directly (bypassing document upload).
    Useful for testing against pre-extracted datasets (TC001-TC010).
    """
    member_id = payload.member_id
    member = _members_db.get(member_id)
    if not member:
        member = Member(
            member_id=member_id,
            name=payload.member_name or member_id,
            join_date=payload.member_join_date or date(2024, 1, 1),
            policy_id=pipeline.policy.policy_id,
        )

    result = pipeline.process_claim(
        member=member,
        claim_amount=payload.claim_amount,
        treatment_date=payload.treatment_date,
        hospital_name=payload.hospital_name,
        is_cashless=payload.is_cashless,
        pre_extracted_data=payload.extracted_data,
        pre_bill_items=payload.bill_items,
        previous_claims_same_day=payload.previous_claims_same_day,
        has_pre_auth=payload.has_pre_authorization,
    )

    # Save to store
    _claims_db[result.claim_id] = {
        "claim_id": result.claim_id,
        "member_id": member_id,
        "claim_amount": payload.claim_amount,
        "approved_amount": result.approved_amount,
        "treatment_date": payload.treatment_date.isoformat(),
        "hospital_name": payload.hospital_name,
        "status": ClaimStatus.DECIDED,
        "decision": result.decision,
        "confidence_score": result.confidence_score,
        "fraud_score": result.fraud_score,
        "trace_summary": [t.model_dump() for t in result.trace_summary],
        "rejection_reasons": result.rejection_reasons,
        "notes": result.notes,
        "created_at": datetime.utcnow().isoformat(),
    }

    return result


@router.post("/policy/chat", response_model=RAGResponse, tags=["Policy Assistant"])
async def chat_policy(
    query: RAGQuery,
    assistant: Generator = Depends(get_rag_assistant),
):
    """
    RAG Policy Assistant endpoint for querying policy guidelines and rules.
    """
    return assistant.ask(query)


@router.get("/claims", tags=["Claims"])
async def list_claims():
    """
    Retrieve all claims in the system (for the dashboard queue).
    """
    claims_list = list(_claims_db.values())
    return {"claims": claims_list}


@router.put("/review/{claim_id}", tags=["Claims"])
async def review_claim(
    claim_id: str,
    action: ReviewAction,
):
    """
    Apply manual adjuster review override to a claim.
    """
    claim = _claims_db.get(claim_id)
    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found.",
        )

    # Apply override
    claim["decision"] = action.override_decision.value
    if action.override_amount is not None:
        claim["approved_amount"] = action.override_amount
    claim["notes"] = action.adjuster_notes
    claim["status"] = ClaimStatus.REVIEWED

    # Update dynamic trace summaries if needed
    claim["trace_summary"].append({
        "step": "manual_review_override",
        "status": "PASS",
        "details": {
            "override_decision": action.override_decision.value,
            "override_amount": action.override_amount,
            "adjuster_notes": action.adjuster_notes,
            "adjuster_id": action.adjuster_id,
        },
        "timestamp": datetime.utcnow().isoformat(),
    })

    return {"message": "Override applied successfully.", "claim_id": claim_id}
