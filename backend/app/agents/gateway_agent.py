import time
from typing import List, Tuple, Dict, Any
from datetime import datetime
from app.agents.base_agent import BaseAgent
from app.models.audit import AuditTraceEntry

class GatewayAgent(BaseAgent):
    """Phase 1: Gateway Agent"""

    def process(self, file_contents: List[Tuple[bytes, str]] = None, claim_id_override: str = None) -> Tuple[str, str, Dict[str, Any], AuditTraceEntry]:
        start = time.time()
        
        claim_id = claim_id_override
        if not claim_id:
            year = datetime.utcnow().year
            claim_id = f"CLM_{year}_{int(time.time() * 1000) % 10000:04d}"

        gateway_status = "PASS"
        gateway_details = {"claim_id": claim_id}

        if file_contents:
            for idx, (file_bytes, mime_type) in enumerate(file_contents):
                size_mb = len(file_bytes) / (1024 * 1024)
                if size_mb > 10.0:
                    gateway_status = "FAIL"
                    gateway_details["error"] = f"File {idx} size ({size_mb:.2f}MB) exceeds 10MB limit."
                    break
                if mime_type not in ["application/pdf", "image/jpeg", "image/png", "image/jpg"]:
                    gateway_status = "FAIL"
                    gateway_details["error"] = f"File {idx} type '{mime_type}' is not supported."
                    break

        trace = self.create_trace("gateway_check", gateway_status, gateway_details, start)
        return gateway_status, claim_id, gateway_details, trace