"""
Plum OPD Claim Adjudication System — FastAPI Application
=========================================================
Entry point for the backend API server.

    uvicorn main:app --reload --port 8000

Features:
  • CORS configured for frontend dev (localhost:3000) and production
  • Versioned API router (/api/v1/…)
  • Health-check endpoint
  • WebSocket endpoint stub for real-time pipeline updates
  • Structured JSON exception handlers
  • Lifespan hooks for startup / shutdown
"""

from __future__ import annotations

# Load .env before anything else reads environment variables
from pathlib import Path as _Path
from dotenv import load_dotenv
# Try backend/.env first, then parent (project root) .env
_env_file = _Path(__file__).parent / ".env"
if not _env_file.exists():
    _env_file = _Path(__file__).parent.parent / ".env"
load_dotenv(_env_file)

import json
import os
import time
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    FastAPI,
    APIRouter,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ── Internal imports ──────────────────────────────────────────────
from app.models.domain import (
    AdjudicationContext,
    AuditTraceEntry,
    ClaimDecision,
    ClaimDecisionOutput,
    ClaimStatus,
    ClaimSubmitRequest,
    ClaimSubmitResponse,
    ClaimStatusResponse,
    ExtractedData,
    HealthResponse,
    Member,
    PolicyTerms,
    RAGQuery,
    RAGResponse,
    ReviewAction,
    RuleEngineResult,
)
from app.engine.rule_engine import DeterministicRuleEngine
from app.services.claim_service import ClaimService


# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

CORS_ORIGINS: List[str] = [
    "http://localhost:3000",         # Next.js dev server
    "http://127.0.0.1:3000",
    "https://plum-opd-system.vercel.app", # Vercel production deployment
    os.getenv("FRONTEND_URL", ""),   # Production frontend
]
# Remove empty strings
CORS_ORIGINS = [o for o in CORS_ORIGINS if o]

# Path to the policy configuration (relative to backend/)
POLICY_TERMS_PATH = Path(__file__).parent / "reference" / "policy_terms.json"
if not POLICY_TERMS_PATH.exists():
    # Fall back to the monorepo reference/ directory
    POLICY_TERMS_PATH = Path(__file__).parent.parent / "reference" / "policy_terms.json"

API_VERSION = "1.0.0"
API_TITLE = "Plum OPD Claim Adjudication System"


# ═══════════════════════════════════════════════════════════════════
# APPLICATION-LEVEL STATE  (loaded once at startup)
# ═══════════════════════════════════════════════════════════════════

# These are populated during the lifespan startup hook.
_policy_terms: Optional[PolicyTerms] = None
_rule_engine: Optional[DeterministicRuleEngine] = None
_claim_service: Optional[ClaimService] = None

# Simple in-memory claim counter (replaced by DB sequence in production)
_claim_counter: int = 0

# In-memory stores (replaced by Supabase in production)
from app.database import IN_MEMORY_CLAIMS as _claims_store
_members_store: Dict[str, Member] = {}


def _load_policy_terms() -> PolicyTerms:
    """Load and validate policy_terms.json into the PolicyTerms model."""
    with open(POLICY_TERMS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return PolicyTerms(**data)


def _seed_test_members(policy_id: str) -> None:
    """Pre-seed member records for the 10 test cases."""
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
        _members_store[m.member_id] = m


# ═══════════════════════════════════════════════════════════════════
# LIFESPAN  (startup / shutdown)
# ═══════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: load policy, initialize engine, seed data."""
    global _policy_terms, _rule_engine, _claim_service

    print("🚀 Starting Plum OPD Adjudication System …")

    # Load policy configuration
    try:
        _policy_terms = _load_policy_terms()
        print(f"   ✅ Policy loaded: {_policy_terms.policy_name}")
    except Exception as exc:
        print(f"   ⚠️  Could not load policy_terms.json: {exc}")
        print("   ⚠️  The /process endpoint will not work until policy is loaded.")

    # Initialize the deterministic rule engine and claim service
    if _policy_terms:
        _rule_engine = DeterministicRuleEngine(_policy_terms)
        _claim_service = ClaimService(_policy_terms)
        print("   ✅ Deterministic Rule Engine initialized")
        print("   ✅ Claim Service initialized (full pipeline)")

    # Seed test members
    if _policy_terms:
        _seed_test_members(_policy_terms.policy_id)
        print(f"   ✅ Seeded {len(_members_store)} test members")

    # Seed policy embeddings for RAG policy assistant
    try:
        from app.rag.retriever import Retriever
        retriever = Retriever()
        retriever.seed_policy_embeddings()
        print("   ✅ RAG policy embeddings indexed / verified")
    except Exception as exc:
        print(f"   ⚠️  Could not seed policy embeddings: {exc}")

    yield   # ── application runs ──

    print("🛑 Shutting down Plum OPD Adjudication System …")


# ═══════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(
    title=API_TITLE,
    description=(
        "AI-augmented, deterministically-decided OPD claim adjudication system. "
        "All financial and policy decisions are made by a pure-Python rule engine — "
        "AI is used only for document extraction and advisory functions."
    ),
    version=API_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── CORS Middleware ───────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handlers ────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "message": "Internal server error",
            "detail": str(exc),
        },
    )


# ═══════════════════════════════════════════════════════════════════
# API ROUTERS
# ═══════════════════════════════════════════════════════════════════

api_v1 = APIRouter(prefix="/api/v1")


# ───────────────────────────────────────────────────────────────────
#  Health
# ───────────────────────────────────────────────────────────────────

@api_v1.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Service health check — returns current status and version."""
    return HealthResponse(
        status="healthy",
        version=API_VERSION,
        service="plum-opd-adjudication",
        timestamp=datetime.utcnow(),
    )


# ───────────────────────────────────────────────────────────────────
#  Claims — Submit
# ───────────────────────────────────────────────────────────────────

@api_v1.post(
    "/claims/submit",
    response_model=ClaimSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Claims"],
)
async def submit_claim(
    payload: ClaimSubmitRequest,
):
    """
    Submit a new OPD claim for adjudication.

    In production this also accepts file uploads (PDF/JPG/PNG).
    For now it accepts JSON with extracted data for test-case execution.
    """
    global _claim_counter
    _claim_counter += 1
    year = datetime.utcnow().year
    claim_id = f"CLM_{year}_{_claim_counter:04d}"

    _claims_store[claim_id] = {
        "claim_id": claim_id,
        "member_id": payload.member_id,
        "claim_amount": payload.claim_amount,
        "treatment_date": payload.treatment_date.isoformat(),
        "hospital_name": payload.hospital_name,
        "is_cashless": payload.is_cashless,
        "status": ClaimStatus.SUBMITTED,
        "created_at": datetime.utcnow().isoformat(),
    }

    return ClaimSubmitResponse(
        claim_id=claim_id,
        status=ClaimStatus.SUBMITTED,
        message=f"Claim {claim_id} submitted successfully. Processing will begin shortly.",
    )


# ───────────────────────────────────────────────────────────────────
#  Claims — Process (run the deterministic engine directly)
# ───────────────────────────────────────────────────────────────────

class ProcessClaimRequest(BaseModel):
    """Direct-process request — bypasses AI extraction for testing."""
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
    # Optional overrides for testing
    member_join_date: Optional[date] = None
    previous_claims_same_day: int = 0


@api_v1.post(
    "/claims/process",
    response_model=ClaimDecisionOutput,
    tags=["Claims"],
)
async def process_claim(payload: ProcessClaimRequest):
    """
    Submit and immediately process a claim through the FULL pipeline:
    Gateway → Extraction → Normalization → Validation → Medical Necessity
    → Deterministic Rule Engine → Fraud Detection → Decision Aggregation.

    Useful for automated testing (TC001–TC010) with pre-extracted data.
    """
    if not _claim_service or not _policy_terms:
        raise HTTPException(
            status_code=503,
            detail="Claim service not initialized — policy_terms.json may be missing",
        )

    # Resolve member
    member = _members_store.get(payload.member_id)
    if not member:
        member = Member(
            member_id=payload.member_id,
            name=payload.member_name or payload.member_id,
            join_date=payload.member_join_date or date(2024, 1, 1),
            policy_id=_policy_terms.policy_id,
        )
    elif payload.member_join_date:
        member = member.model_copy(update={"join_date": payload.member_join_date})

    # Run the full ClaimService pipeline
    result = _claim_service.process_claim(
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

    # Store the processed claim
    _claims_store[result.claim_id] = {
        "claim_id": result.claim_id,
        "member_id": payload.member_id,
        "claim_amount": payload.claim_amount,
        "approved_amount": result.approved_amount,
        "treatment_date": payload.treatment_date.isoformat(),
        "hospital_name": payload.hospital_name,
        "status": "DECIDED",
        "decision": result.decision,
        "confidence_score": result.confidence_score,
        "confidence_breakdown": result.confidence_breakdown.model_dump() if result.confidence_breakdown else None,
        "fraud_score": result.fraud_score,
        "trace_summary": [t.model_dump() for t in result.trace_summary],
        "rejection_reasons": result.rejection_reasons,
        "notes": result.notes,
        "created_at": datetime.utcnow().isoformat(),
        "investigator_report": result.investigator_report.model_dump() if result.investigator_report else None,
    }

    return result

# ───────────────────────────────────────────────────────────────────
#  Claims — Upload (Multimodal AI Extraction pipeline)
# ───────────────────────────────────────────────────────────────────

_ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/jpg"}
_MAX_FILE_SIZE_MB = 10.0

@api_v1.post(
    "/claims/upload",
    response_model=ClaimDecisionOutput,
    tags=["Claims"],
)
async def upload_and_process_claim(
    files: List[UploadFile] = File(..., description="Medical documents (PDF, JPG, PNG)"),
    member_id: str = Form(...),
    treatment_date: str = Form(..., description="Treatment date (YYYY-MM-DD)"),
    claim_amount: float = Form(...),
    hospital_name: Optional[str] = Form(None),
    is_cashless: bool = Form(False),
    has_pre_authorization: bool = Form(False),
):
    """
    Upload medical documents and process a claim through the FULL AI pipeline:

    1. **Gateway** — Validate file types and sizes
    2. **AI Extraction** — Gemini 2.5 Flash extracts structured data from documents
    3. **Normalization** — Standardize dates, doctor registration, amounts, provider names
    4. **Validation** — Cross-field checks (patient name, date, doctor registration)
    5. **Medical Necessity** — Gemini advisory check
    6. **Rule Engine** — Deterministic coverage, financial, eligibility checks
    7. **Fraud Detection** — Rule-based + vector similarity
    8. **Decision Aggregation** — Final APPROVED/PARTIAL/REJECTED/MANUAL_REVIEW

    Accepts multipart form data with one or more file attachments.
    """
    if not _claim_service or not _policy_terms:
        raise HTTPException(
            status_code=503,
            detail="Claim service not initialized — policy_terms.json may be missing",
        )

    # Validate and read uploaded files
    file_contents = []
    for f in files:
        # Validate MIME type
        content_type = f.content_type or "application/octet-stream"
        if content_type not in _ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"File '{f.filename}' has unsupported type '{content_type}'. "
                       f"Allowed: PDF, JPG, PNG.",
            )

        # Read file bytes
        file_bytes = await f.read()

        # Validate file size
        size_mb = len(file_bytes) / (1024 * 1024)
        if size_mb > _MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=400,
                detail=f"File '{f.filename}' ({size_mb:.1f}MB) exceeds {_MAX_FILE_SIZE_MB}MB limit.",
            )

        file_contents.append((file_bytes, content_type))

    # Parse treatment date
    try:
        parsed_date = date.fromisoformat(treatment_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid treatment_date format '{treatment_date}'. Use YYYY-MM-DD.",
        )

    # Resolve member
    member = _members_store.get(member_id)
    if not member:
        member = Member(
            member_id=member_id,
            name=member_id,
            join_date=date(2024, 1, 1),
            policy_id=_policy_terms.policy_id,
        )

    # Run the full ClaimService pipeline with AI extraction
    result = _claim_service.process_claim(
        member=member,
        claim_amount=claim_amount,
        treatment_date=parsed_date,
        hospital_name=hospital_name,
        is_cashless=is_cashless,
        file_contents=file_contents,
        has_pre_auth=has_pre_authorization,
    )

    # Store the processed claim
    _claims_store[result.claim_id] = {
        "claim_id": result.claim_id,
        "member_id": member_id,
        "claim_amount": claim_amount,
        "approved_amount": result.approved_amount,
        "treatment_date": parsed_date.isoformat(),
        "hospital_name": hospital_name,
        "status": "DECIDED",
        "decision": result.decision,
        "confidence_score": result.confidence_score,
        "confidence_breakdown": result.confidence_breakdown.model_dump() if result.confidence_breakdown else None,
        "fraud_score": result.fraud_score,
        "trace_summary": [t.model_dump() for t in result.trace_summary],
        "rejection_reasons": result.rejection_reasons,
        "notes": result.notes,
        "created_at": datetime.utcnow().isoformat(),
        "extraction_method": "AI_MULTIMODAL",
        "investigator_report": result.investigator_report.model_dump() if result.investigator_report else None,
    }

    return result


# ───────────────────────────────────────────────────────────────────
#  Claims — Get by ID
# ───────────────────────────────────────────────────────────────────

@api_v1.get("/claims/{claim_id}", tags=["Claims"])
async def get_claim(claim_id: str):
    claim = _claims_store.get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    return claim


# ───────────────────────────────────────────────────────────────────
#  Claims — List
# ───────────────────────────────────────────────────────────────────

@api_v1.get("/claims", tags=["Claims"])
async def list_claims(
    page: int = 1,
    page_size: int = 20,
    status_filter: Optional[str] = None,
):
    claims = list(_claims_store.values())
    if status_filter:
        claims = [c for c in claims if c.get("status") == status_filter]
    total = len(claims)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "claims": claims[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ───────────────────────────────────────────────────────────────────
#  Claims — Status
# ───────────────────────────────────────────────────────────────────

@api_v1.get("/claims/{claim_id}/status", tags=["Claims"])
async def get_claim_status(claim_id: str):
    """
    Retrieve adjudication status, full Trace Ledger, and Dynamic Investigator Report.
    """
    claim = _claims_store.get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    
    return {
        "claim_id": claim_id,
        "status": claim.get("status", "DECIDED"),
        "decision": claim.get("decision"),
        "approved_amount": claim.get("approved_amount", 0.0),
        "confidence_score": claim.get("confidence_score", 0.0),
        "confidence_breakdown": claim.get("confidence_breakdown"),
        "fraud_score": claim.get("fraud_score", 0.0),
        "trace_ledger": claim.get("trace_summary", []),
        "trace_summary": claim.get("trace_summary", []),
        "investigator_report": claim.get("investigator_report", {}),
    }


# ───────────────────────────────────────────────────────────────────
#  Trace Ledger
# ───────────────────────────────────────────────────────────────────

@api_v1.get("/claims/{claim_id}/trace", tags=["Traces"])
async def get_trace(claim_id: str):
    """Get the full audit trace ledger for a claim."""
    claim = _claims_store.get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    return {"claim_id": claim_id, "traces": claim.get("trace_summary", []), "message": "Success"}


# ───────────────────────────────────────────────────────────────────
#  Investigator Report
# ───────────────────────────────────────────────────────────────────

@api_v1.get("/claims/{claim_id}/report", tags=["Reports"])
async def get_report(claim_id: str):
    """Get the investigator report for a claim."""
    claim = _claims_store.get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    return {"claim_id": claim_id, "report": claim.get("investigator_report", {}), "message": "Success"}


# ───────────────────────────────────────────────────────────────────
#  Fraud Signals
# ───────────────────────────────────────────────────────────────────

@api_v1.get("/claims/{claim_id}/fraud", tags=["Fraud"])
async def get_fraud_signals(claim_id: str):
    """Get fraud detection signals for a claim."""
    claim = _claims_store.get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    report = claim.get("investigator_report") or {}
    fraud_analysis = report.get("fraud_analysis") or {}
    return {
        "claim_id": claim_id,
        "signals": fraud_analysis.get("signals", []),
        "fraud_score": claim.get("fraud_score", 0.0),
    }


# ───────────────────────────────────────────────────────────────────
#  RAG Policy Assistant
# ───────────────────────────────────────────────────────────────────

@api_v1.post("/policy/chat", response_model=RAGResponse, tags=["Policy Assistant"])
async def chat_policy(query: RAGQuery):
    """
    Ask a natural-language question about the insurance policy.
    Uses RAG (Retrieval-Augmented Generation) over policy_terms.json
    and adjudication_rules.md.
    """
    from app.rag.generator import Generator
    assistant = Generator()
    return assistant.ask(query)


@api_v1.post("/policy/ask", response_model=RAGResponse, tags=["Policy Assistant"])
async def ask_policy(query: RAGQuery):
    """
    Query the policy assistant (compatibility alias).
    """
    from app.rag.generator import Generator
    assistant = Generator()
    return assistant.ask(query)


# ───────────────────────────────────────────────────────────────────
#  Manual Review Queue
# ───────────────────────────────────────────────────────────────────

@api_v1.get("/review/queue", tags=["Manual Review"])
async def get_review_queue():
    """Get the manual review queue for adjusters."""
    claims = list(_claims_store.values())
    queue = [c for c in claims if c.get("decision") == "MANUAL_REVIEW" or c.get("status") == "UNDER_REVIEW"]
    return {"queue": queue, "total": len(queue)}


@api_v1.put("/review/{claim_id}", tags=["Manual Review"])
async def submit_review(claim_id: str, action: ReviewAction):
    """Submit an adjuster's override decision for a claim in manual review."""
    claim = _claims_store.get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    
    claim["decision"] = action.override_decision.value
    if action.override_amount is not None:
        claim["approved_amount"] = action.override_amount
    claim["notes"] = action.adjuster_notes
    claim["status"] = "REVIEWED"
    
    # Append a trace entry
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
    
    # Update investigator report text if present
    if claim.get("investigator_report"):
        claim["investigator_report"]["decision_rationale"]["decision"] = action.override_decision.value
        claim["investigator_report"]["decision_rationale"]["notes"] = action.adjuster_notes
        
    return {"message": "Override applied successfully.", "claim_id": claim_id}


# ───────────────────────────────────────────────────────────────────
#  Decision
# ───────────────────────────────────────────────────────────────────

@api_v1.get("/claims/{claim_id}/decision", tags=["Decisions"])
async def get_decision(claim_id: str):
    """Get the adjudication decision for a claim."""
    claim = _claims_store.get(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    return {"claim_id": claim_id, "decision": claim.get("decision"), "approved_amount": claim.get("approved_amount", 0.0)}


# ───────────────────────────────────────────────────────────────────
#  WebSocket — Real-Time Pipeline Updates
# ───────────────────────────────────────────────────────────────────

@app.websocket("/ws/{claim_id}")
async def websocket_pipeline(websocket: WebSocket, claim_id: str):
    """
    WebSocket endpoint for real-time pipeline progress updates.
    The frontend connects here after submitting a claim to watch
    each processing stage complete.
    """
    await websocket.accept()
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "claim_id": claim_id,
            "message": "Connected to pipeline updates",
        })
        # Keep alive — in production the pipeline service pushes updates here
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({
                "type": "ack",
                "claim_id": claim_id,
                "received": data,
            })
    except WebSocketDisconnect:
        pass


# ═══════════════════════════════════════════════════════════════════
# REGISTER ROUTER
# ═══════════════════════════════════════════════════════════════════

app.include_router(api_v1)


# ═══════════════════════════════════════════════════════════════════
# ROOT REDIRECT
# ═══════════════════════════════════════════════════════════════════

@app.get("/", tags=["Root"])
async def root():
    return {
        "service": API_TITLE,
        "version": API_VERSION,
        "docs": "/docs",
        "health": "/api/v1/health",
    }


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def _determine_next_steps(result: RuleEngineResult) -> str:
    """Generate user-facing next-steps text based on the decision."""
    if result.decision == ClaimDecision.APPROVED:
        return "Your claim has been approved. The approved amount will be processed for reimbursement."
    elif result.decision == ClaimDecision.PARTIAL:
        return (
            "Your claim has been partially approved. Excluded items have been rejected. "
            "You may appeal the excluded items through the Policy Assistant."
        )
    elif result.decision == ClaimDecision.MANUAL_REVIEW:
        return (
            "Your claim has been flagged for manual review. "
            "An adjuster will review your claim within 2 business days."
        )
    elif result.decision == ClaimDecision.REJECTED:
        reasons = ", ".join(result.rejection_reasons)
        return (
            f"Your claim has been rejected due to: {reasons}. "
            "If you believe this is incorrect, please submit an appeal with additional documentation."
        )
    return "Your claim is being processed."


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
