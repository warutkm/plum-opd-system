import time
from typing import Any, Dict
from app.models.audit import AuditTraceEntry

class BaseAgent:
    """Base class for all agents."""

    def create_trace(
        self,
        step: str,
        status: str,
        details: Dict[str, Any],
        start_time: float,
    ) -> AuditTraceEntry:
        """Helper to append a trace step with duration in ms."""
        duration_ms = int((time.time() - start_time) * 1000)
        return AuditTraceEntry(
            step=step,
            status=status,
            details=details,
            duration_ms=duration_ms,
        )