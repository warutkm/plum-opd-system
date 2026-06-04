from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class TraceStatus(str, Enum):
    """Status value recorded in the audit trace ledger."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    SKIP = "SKIP"
    ERROR = "ERROR"
    PENDING = "PENDING"

class AuditTraceEntry(BaseModel):
    """A single row in the Trace Ledger."""
    step: str
    status: str = "PENDING"
    details: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[int] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
