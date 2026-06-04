from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, date
from app.models.claim import ClaimDecision, ClaimStatus
from app.models.audit import AuditTraceEntry
from app.models.report import InvestigatorReport
from app.schemas.decision_schema import ConfidenceBreakdown

class ClaimDecisionOutput(BaseModel):
    claim_id: str
    decision: str
    approved_amount: float = 0.0
    rejection_reasons: List[str] = Field(default_factory=list)
    rejected_items: List[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    fraud_score: float = 0.0
    notes: str = ""
    next_steps: str = ""
    is_cashless_approved: bool = False
    network_discount: float = 0.0
    deductions: Dict[str, float] = Field(default_factory=dict)
    trace_summary: List[AuditTraceEntry] = Field(default_factory=list)
    investigator_report: Optional[InvestigatorReport] = None
    confidence_breakdown: Optional[ConfidenceBreakdown] = None

class ReviewAction(BaseModel):
    claim_id: str
    override_decision: ClaimDecision
    override_amount: Optional[float] = None
    adjuster_notes: str = ""
    adjuster_id: str = ""

class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    service: str = "plum-opd-adjudication"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ClaimSubmitRequest(BaseModel):
    member_id: str
    member_name: Optional[str] = None
    treatment_date: date
    claim_amount: float
    hospital_name: Optional[str] = None
    is_cashless: bool = False

class ClaimSubmitResponse(BaseModel):
    claim_id: str
    status: ClaimStatus
    message: str = "Claim submitted successfully"

class ClaimStatusResponse(BaseModel):
    claim_id: str
    status: ClaimStatus
    decision: Optional[ClaimDecision] = None
    approved_amount: float = 0.0
    confidence_score: float = 0.0
    fraud_score: float = 0.0
    traces: List[AuditTraceEntry] = Field(default_factory=list)
