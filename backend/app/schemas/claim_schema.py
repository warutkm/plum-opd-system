from __future__ import annotations
from datetime import date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.member import Member
from app.models.audit import AuditTraceEntry

class ExtractedData(BaseModel):
    """Structured data that the AI Extraction Agent produces from documents."""
    patient_name: Optional[str] = None
    bill_number: Optional[str] = None
    age: Optional[str] = None
    doctor_name: Optional[str] = None
    doctor_registration: Optional[str] = None
    diagnosis: Optional[str] = None
    medicines: List[str] = Field(default_factory=list)
    procedures: List[str] = Field(default_factory=list)
    tests: List[str] = Field(default_factory=list)
    provider_name: Optional[str] = None
    bill_amount: Optional[float] = None
    treatment_date: Optional[date] = None
    bill_items: Dict[str, float] = Field(default_factory=dict)
    extraction_confidence: float = 0.0
    raw_extraction: Dict[str, Any] = Field(default_factory=dict)
    normalized_data: Dict[str, Any] = Field(default_factory=dict)

class AdjudicationContext(BaseModel):
    """
    Everything the deterministic rule engine needs to process one claim.
    """
    claim_id: str
    member: Member
    claim_amount: float
    treatment_date: date
    documents_submitted: List[str] = Field(default_factory=list)
    extracted_data: ExtractedData = Field(default_factory=ExtractedData)
    bill_items: Dict[str, float] = Field(default_factory=dict)
    hospital_name: Optional[str] = None
    is_cashless: bool = False
    is_network_hospital: bool = False
    has_pre_authorization: bool = False
    ytd_approved_total: float = 0.0
    previous_claims_count_24h: int = 0
