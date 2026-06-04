"""
Tests for the Trace Ledger (Point 9 from the architecture document).

Verifies:
    1. Complete audit trail generation for successful claims.
    2. Proper sequencing of steps in the pipeline (Gateway -> Doc Verifier -> ... -> Decision Aggregator).
    3. Proper skip handling (e.g. skipping extraction when documents are missing).
    4. Early termination (early-exit) on Gateway file validation failure.
    5. Integrity of trace details (durations, timestamps, status values).
"""

import pytest
from datetime import date
from unittest.mock import patch

from app.models.audit import AuditTraceEntry
from app.models.claim import ClaimDecision
from app.schemas.claim_schema import ExtractedData
from app.schemas.decision_schema import RuleEngineResult, MedicalNecessityResult
from app.models.fraud import FraudResult
from app.services.claim_service import ClaimService
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def tc001_payload():
    return {
        "member_id": "EMP001",
        "member_name": "Rajesh Kumar",
        "treatment_date": "2024-11-01",
        "claim_amount": 1500,
        "extracted_data": {
            "patient_name": "Rajesh Kumar",
            "doctor_name": "Dr. Sharma",
            "doctor_registration": "KA/45678/2015",
            "diagnosis": "Viral fever",
            "medicines": ["Paracetamol 650mg", "Vitamin C"],
            "tests": ["CBC", "Dengue test"],
            "treatment_date": "2024-11-01",
            "bill_items": {"consultation_fee": 1000, "diagnostic_tests": 500},
            "extraction_confidence": 0.95,
        },
        "bill_items": {"consultation_fee": 1000, "diagnostic_tests": 500},
    }


def test_complete_pipeline_trace_ledger_sequencing(client, tc001_payload):
    """Verify that a successful claim executes all 11 stages of the pipeline in order."""
    with patch("app.agents.medical_necessity_agent.MedicalNecessityAgent.process") as mock_necessity:
        mock_necessity.return_value = MedicalNecessityResult(
            medically_necessary=True, reasoning="Standard consultation", confidence=0.95
        )

        response = client.post("/api/v1/claims/process", json=tc001_payload)
        assert response.status_code == 200
        data = response.json()
        
        traces = data["trace_summary"]
        assert len(traces) == 11
        
        # Verify exact sequence
        expected_steps = [
            "gateway_check",
            "doc_verification",
            "ai_extraction",
            "normalization",
            "cross_validation",
            "medical_necessity_check",
            "deterministic_rules_check",
            "fraud_detection_check",
            "vector_fraud_check",
            "confidence_engine",
            "decision_aggregator",
        ]
        
        for i, expected_step in enumerate(expected_steps):
            assert traces[i]["step"] == expected_step
            assert traces[i]["status"] in ["PASS", "WARNING", "SKIP"]
            assert traces[i]["duration_ms"] is not None
            assert traces[i]["timestamp"] is not None


def test_early_exit_on_gateway_failure(client, tc001_payload):
    """Verify that if gateway validation fails, execution stops immediately and trace ledger has length 1."""
    # Force gateway failure by mocking gateway process response
    with patch("app.agents.gateway_agent.GatewayAgent.process") as mock_gateway:
        mock_gateway.return_value = (
            "FAIL",
            "CLM_ERROR",
            {"error": "Unsupported file format"},
            AuditTraceEntry(step="gateway_check", status="FAIL", details={"error": "Unsupported file format"}),
        )

        response = client.post("/api/v1/claims/process", json=tc001_payload)
        assert response.status_code == 200
        data = response.json()
        
        assert data["decision"] == "REJECTED"
        assert "GATEWAY_FILE_INVALID" in data["rejection_reasons"]
        
        # Only the gateway step trace should exist
        traces = data["trace_summary"]
        assert len(traces) == 1
        assert traces[0]["step"] == "gateway_check"
        assert traces[0]["status"] == "FAIL"
        assert traces[0]["details"]["error"] == "Unsupported file format"


def test_skip_status_on_extraction_bypass(client, tc001_payload):
    """Verify that bypassing multimodal extraction correctly tags the trace status as SKIP."""
    # When processing via JSON (claims/process), file contents are missing, 
    # so extraction agent is skipped
    with patch("app.agents.medical_necessity_agent.MedicalNecessityAgent.process") as mock_necessity:
        mock_necessity.return_value = MedicalNecessityResult(
            medically_necessary=True, reasoning="Standard consultation", confidence=0.95
        )

        response = client.post("/api/v1/claims/process", json=tc001_payload)
        assert response.status_code == 200
        data = response.json()
        
        traces = data["trace_summary"]
        # Finding the ai_extraction step
        extraction_trace = next(t for t in traces if t["step"] == "ai_extraction")
        assert extraction_trace["status"] == "SKIP"


def test_trace_properties_validity(client, tc001_payload):
    """Verify that traces contain valid datatypes for all model attributes."""
    with patch("app.agents.medical_necessity_agent.MedicalNecessityAgent.process") as mock_necessity:
        mock_necessity.return_value = MedicalNecessityResult(
            medically_necessary=True, reasoning="Standard consultation", confidence=0.95
        )

        response = client.post("/api/v1/claims/process", json=tc001_payload)
        assert response.status_code == 200
        data = response.json()
        
        for trace in data["trace_summary"]:
            assert isinstance(trace["step"], str)
            assert isinstance(trace["status"], str)
            assert isinstance(trace["details"], dict)
            assert isinstance(trace["duration_ms"], int)
            assert isinstance(trace["timestamp"], str)
