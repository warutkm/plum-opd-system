from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from app.models.claim import ClaimDecision

class ReviewPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class ReviewStatus(str, Enum):
    QUEUED = "QUEUED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"

class ManualReviewItem(BaseModel):
    claim_id: str
    priority: ReviewPriority = ReviewPriority.MEDIUM
    reason: str = ""
    fraud_score: float = 0.0
    confidence_score: float = 0.0
    assigned_to: Optional[str] = None
    status: ReviewStatus = ReviewStatus.QUEUED

class ReviewAction(BaseModel):
    claim_id: str
    override_decision: ClaimDecision
    override_amount: Optional[float] = None
    adjuster_notes: str = ""
    adjuster_id: str = ""
