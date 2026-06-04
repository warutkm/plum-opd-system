from __future__ import annotations
from enum import Enum

class ClaimStatus(str, Enum):
    """Lifecycle status of a claim inside the processing pipeline."""
    SUBMITTED = "SUBMITTED"
    PROCESSING = "PROCESSING"
    EXTRACTION = "EXTRACTION"
    VALIDATION = "VALIDATION"
    FRAUD_CHECK = "FRAUD_CHECK"
    DECISION_PENDING = "DECISION_PENDING"
    DECIDED = "DECIDED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    REVIEWED = "REVIEWED"
    CLOSED = "CLOSED"
    ERROR = "ERROR"

class ClaimDecision(str, Enum):
    """Final adjudication decision for a claim."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PARTIAL = "PARTIAL"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    PENDING = "PENDING"

class ClaimCategory(str, Enum):
    """Coverage category used for sub-limit / copay resolution."""
    CONSULTATION = "consultation"
    DIAGNOSTIC = "diagnostic"
    PHARMACY = "pharmacy"
    DENTAL = "dental"
    VISION = "vision"
    ALTERNATIVE_MEDICINE = "alternative_medicine"
    MIXED = "mixed"