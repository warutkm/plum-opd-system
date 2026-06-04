from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List
from pydantic import BaseModel, Field

class FraudEngine(str, Enum):
    RULE_BASED = "RULE_BASED"
    VECTOR_SIMILARITY = "VECTOR_SIMILARITY"

class FraudSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class FraudSignal(BaseModel):
    signal_type: str
    engine: FraudEngine
    description: str
    severity: FraudSeverity = FraudSeverity.LOW
    score_impact: float = 0.0
    details: Dict[str, Any] = Field(default_factory=dict)

class FraudResult(BaseModel):
    fraud_score: float = 0.0
    signals: List[FraudSignal] = Field(default_factory=list)
    requires_manual_review: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)
