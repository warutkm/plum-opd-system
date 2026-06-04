from __future__ import annotations
from datetime import date
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.claim import ClaimDecision
from app.models.audit import AuditTraceEntry

class CoverageItem(BaseModel):
    item: str
    amount: float = 0.0
    category: str = ""
    is_covered: bool = True
    exclusion_reason: Optional[str] = None

class EligibilityResult(BaseModel):
    module: str = "eligibility"
    passed: bool = False
    status: str = "PENDING"
    policy_active: bool = False
    member_covered: bool = False
    waiting_period_satisfied: bool = False
    waiting_period_end_date: Optional[date] = None
    rejection_reasons: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)

class DocumentationResult(BaseModel):
    module: str = "documentation"
    passed: bool = False
    status: str = "PENDING"
    has_prescription: bool = False
    has_bill: bool = False
    doctor_reg_valid: bool = False
    patient_match: bool = True
    date_consistent: bool = True
    rejection_reasons: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)

class CoverageResult(BaseModel):
    module: str = "coverage"
    passed: bool = False
    status: str = "PENDING"
    primary_category: str = "consultation"
    covered_items: List[CoverageItem] = Field(default_factory=list)
    excluded_items: List[CoverageItem] = Field(default_factory=list)
    has_covered_items: bool = False
    has_excluded_items: bool = False
    pre_auth_required: bool = False
    pre_auth_satisfied: bool = False
    rejection_reasons: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)

class FinancialBreakdown(BaseModel):
    base_amount: float = 0.0
    covered_amount: float = 0.0
    copay_percentage: float = 0.0
    copay_amount: float = 0.0
    network_discount_percentage: float = 0.0
    network_discount_amount: float = 0.0
    deductible_amount: float = 0.0
    sub_limit_cap: float = 0.0
    per_claim_limit_cap: float = 0.0
    annual_limit_remaining: float = 0.0
    final_approved_amount: float = 0.0

class FinancialResult(BaseModel):
    module: str = "financial"
    passed: bool = False
    status: str = "PENDING"
    approved_amount: float = 0.0
    breakdown: FinancialBreakdown = Field(default_factory=FinancialBreakdown)
    is_cashless_approved: bool = False
    rejection_reasons: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)

class PartialApprovalResult(BaseModel):
    module: str = "partial_approval"
    passed: bool = False
    status: str = "PENDING"
    approved_items: List[CoverageItem] = Field(default_factory=list)
    rejected_items: List[CoverageItem] = Field(default_factory=list)
    approved_amount: float = 0.0
    rejected_amount: float = 0.0
    details: Dict[str, Any] = Field(default_factory=dict)

class RuleEngineResult(BaseModel):
    decision: ClaimDecision
    approved_amount: float = 0.0
    rejection_reasons: List[str] = Field(default_factory=list)
    rejected_items: List[str] = Field(default_factory=list)
    notes: str = ""
    rule_confidence: float = 1.0
    is_cashless_approved: bool = False
    eligibility: Optional[EligibilityResult] = None
    documentation: Optional[DocumentationResult] = None
    coverage: Optional[CoverageResult] = None
    financial: Optional[FinancialResult] = None
    partial_approval: Optional[PartialApprovalResult] = None
    traces: List[AuditTraceEntry] = Field(default_factory=list)



class MedicalNecessityResult(BaseModel):
    medically_necessary: bool = True
    reasoning: str = ""
    confidence: float = 0.0

class ConfidenceBreakdown(BaseModel):
    extraction_confidence: float = 0.0
    rule_confidence: float = 0.0
    fraud_doc_quality: float = 0.0
    final_confidence: float = 0.0
