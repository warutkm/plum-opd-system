from __future__ import annotations
from enum import Enum

class DocumentType(str, Enum):
    """Types of medical documents accepted by the system."""
    PRESCRIPTION = "PRESCRIPTION"
    MEDICAL_BILL = "MEDICAL_BILL"
    DIAGNOSTIC_REPORT = "DIAGNOSTIC_REPORT"
    PHARMACY_BILL = "PHARMACY_BILL"
    OTHER = "OTHER"