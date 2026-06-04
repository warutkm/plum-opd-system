from __future__ import annotations
from typing import Any, Dict, List
from pydantic import BaseModel, Field

class InvestigatorReport(BaseModel):
    """Comprehensive investigator report with 6 sections."""
    claim_summary: Dict[str, Any] = Field(default_factory=dict)
    coverage_analysis: Dict[str, Any] = Field(default_factory=dict)
    limit_analysis: Dict[str, Any] = Field(default_factory=dict)
    fraud_analysis: Dict[str, Any] = Field(default_factory=dict)
    decision_rationale: Dict[str, Any] = Field(default_factory=dict)
    what_if_analysis: Dict[str, Any] = Field(default_factory=dict)
    policy_references: List[Dict[str, Any]] = Field(default_factory=list)
    full_report_text: str = ""
