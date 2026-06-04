import time
from datetime import date
from typing import Dict, Any, Tuple
from app.agents.base_agent import BaseAgent
from app.models.audit import AuditTraceEntry
from app.schemas.claim_schema import ExtractedData
from app.models.member import Member
from app.utils.validators import validate_doctor_registration

class ValidationAgent(BaseAgent):
    """Phase 2B: Cross-field Validation"""

    def process(self, extracted_data: ExtractedData, member: Member, treatment_date: date) -> Tuple[str, Dict[str, Any], AuditTraceEntry]:
        start = time.time()
        val_status = "PASS"
        val_details = {}

        # Patient name cross-match
        member_parts = set(member.name.lower().split())
        patient_parts = set((extracted_data.patient_name or "").lower().split())
        name_match = len(member_parts.intersection(patient_parts)) > 0
        val_details["patient_name_match"] = name_match

        # Date consistency
        date_consistent = True
        if extracted_data.treatment_date and extracted_data.treatment_date != treatment_date:
            date_consistent = False
        val_details["date_consistency"] = date_consistent

        # Doctor registration pattern validation
        doc_reg_valid = False
        if extracted_data.doctor_registration:
            doc_reg_valid = validate_doctor_registration(extracted_data.doctor_registration)
        val_details["doctor_reg_format_valid"] = doc_reg_valid

        if not name_match or not date_consistent or not doc_reg_valid:
            val_status = "WARNING"

        trace = self.create_trace("cross_validation", val_status, val_details, start)
        return val_status, val_details, trace