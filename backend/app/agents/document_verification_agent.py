import time
from typing import List, Tuple, Dict, Any, Optional
from app.agents.base_agent import BaseAgent
from app.models.audit import AuditTraceEntry
from app.schemas.claim_schema import ExtractedData

class DocumentVerificationAgent(BaseAgent):
    """Phase 1: Document Verification"""

    def process(self, file_contents: List[Tuple[bytes, str]] = None, pre_extracted_data: Optional[ExtractedData] = None, pre_bill_items: Optional[Dict[str, float]] = None) -> Tuple[str, Dict[str, Any], AuditTraceEntry]:
        start = time.time()
        doc_status = "PASS"
        doc_details = {}

        if file_contents:
            has_presc = len(file_contents) > 1
            has_bill = len(file_contents) > 0
        else:
            has_presc = pre_extracted_data is not None and (
                pre_extracted_data.doctor_registration is not None or pre_extracted_data.diagnosis is not None
            )
            has_bill = pre_bill_items is not None or (
                pre_extracted_data is not None and len(pre_extracted_data.bill_items) > 0
            )

        if not has_presc or not has_bill:
            doc_status = "FAIL"
            doc_details["error"] = "Missing required documentation: prescription or bill."
            doc_details["has_prescription"] = has_presc
            doc_details["has_bill"] = has_bill

        trace = self.create_trace("doc_verification", doc_status, doc_details, start)
        return doc_status, doc_details, trace