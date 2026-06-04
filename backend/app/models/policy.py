from __future__ import annotations
from typing import List
from pydantic import BaseModel, Field

class PolicyHolder(BaseModel):
    company: str
    employees_covered: int
    dependents_covered: bool

class ConsultationCoverage(BaseModel):
    covered: bool
    sub_limit: float
    copay_percentage: float
    network_discount: float

class DiagnosticCoverage(BaseModel):
    covered: bool
    sub_limit: float
    pre_authorization_required: bool
    covered_tests: List[str] = Field(default_factory=list)

class PharmacyCoverage(BaseModel):
    covered: bool
    sub_limit: float
    generic_drugs_mandatory: bool
    branded_drugs_copay: float

class DentalCoverage(BaseModel):
    covered: bool
    sub_limit: float
    routine_checkup_limit: float
    procedures_covered: List[str] = Field(default_factory=list)
    cosmetic_procedures: bool

class VisionCoverage(BaseModel):
    covered: bool
    sub_limit: float
    eye_test_covered: bool
    glasses_contact_lenses: bool
    lasik_surgery: bool

class AlternativeMedicineCoverage(BaseModel):
    covered: bool
    sub_limit: float
    covered_treatments: List[str] = Field(default_factory=list)
    therapy_sessions_limit: int

class CoverageDetails(BaseModel):
    annual_limit: float
    per_claim_limit: float
    family_floater_limit: float
    consultation_fees: ConsultationCoverage
    diagnostic_tests: DiagnosticCoverage
    pharmacy: PharmacyCoverage
    dental: DentalCoverage
    vision: VisionCoverage
    alternative_medicine: AlternativeMedicineCoverage

class SpecificAilments(BaseModel):
    diabetes: int = 90
    hypertension: int = 90
    joint_replacement: int = 730

class WaitingPeriods(BaseModel):
    initial_waiting: int
    pre_existing_diseases: int
    maternity: int
    specific_ailments: SpecificAilments

class ClaimRequirements(BaseModel):
    documents_required: List[str] = Field(default_factory=list)
    submission_timeline_days: int = 30
    minimum_claim_amount: float = 500

class CashlessFacilities(BaseModel):
    available: bool
    network_only: bool
    pre_approval_required: bool
    instant_approval_limit: float

class PolicyTerms(BaseModel):
    """Complete insurance policy configuration loaded from policy_terms.json."""
    policy_id: str
    policy_name: str
    effective_date: str
    policy_holder: PolicyHolder
    coverage_details: CoverageDetails
    waiting_periods: WaitingPeriods
    exclusions: List[str] = Field(default_factory=list)
    claim_requirements: ClaimRequirements
    network_hospitals: List[str] = Field(default_factory=list)
    cashless_facilities: CashlessFacilities