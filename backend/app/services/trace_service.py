from typing import List, Dict, Any
from app.models.audit import AuditTraceEntry

class TraceService:
    def format_trace_ledger(self, traces: List[AuditTraceEntry]) -> Dict[str, Any]:
        return {
            "total_steps": len(traces),
            "ledger": [
                {
                    "step": trace.step,
                    "status": trace.status,
                    "duration_ms": trace.duration_ms,
                    "timestamp": trace.timestamp.isoformat() if hasattr(trace.timestamp, 'isoformat') else trace.timestamp,
                    "details": trace.details
                }
                for trace in traces
            ]
        }