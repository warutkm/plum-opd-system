"""
Plum OPD Claim Adjudication System — Pytest Suite
===================================================
Tests API endpoints and pipeline logic for TC001, TC002, TC005, and TC008
using mock data and FastAPI TestClient with proper lifespan lifecycle handling.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path to enable local imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app
from app.models.domain import ClaimDecision, ExtractedData
from app.schemas.decision_schema import MedicalNecessityResult





# ── MOCK DATA FOR TEST CASES ─────────────────────────────────────

@pytest.fixture
def tc001_payload():
    """TC001: Simple Consultation - Approved (Reimbursement)"""
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


@pytest.fixture
def tc002_payload():
    """TC002: Dental Treatment - Partial Approval"""
    return {
        "member_id": "EMP002",
        "member_name": "Priya Singh",
        "treatment_date": "2024-10-15",
        "claim_amount": 12000,
        "extracted_data": {
            "patient_name": "Priya Singh",
            "doctor_name": "Dr. Patel",
            "doctor_registration": "MH/23456/2018",
            "diagnosis": "Tooth decay requiring root canal",
            "procedures": ["Root canal treatment", "Teeth whitening"],
            "treatment_date": "2024-10-15",
            "bill_items": {"root_canal": 8000, "teeth_whitening": 4000},
            "extraction_confidence": 0.92,
        },
        "bill_items": {"root_canal": 8000, "teeth_whitening": 4000},
    }


@pytest.fixture
def tc005_payload():
    """TC005: Pre-existing Condition - Waiting Period Check"""
    return {
        "member_id": "EMP005",
        "member_name": "Vikram Joshi",
        "member_join_date": "2024-09-01",
        "treatment_date": "2024-10-15",
        "claim_amount": 3000,
        "extracted_data": {
            "patient_name": "Vikram Joshi",
            "doctor_name": "Dr. Mehta",
            "doctor_registration": "GJ/56789/2014",
            "diagnosis": "Type 2 Diabetes",
            "medicines": ["Metformin", "Glimepiride"],
            "treatment_date": "2024-10-15",
            "bill_items": {"consultation_fee": 1000, "medicines": 2000},
            "extraction_confidence": 0.96,
        },
        "bill_items": {"consultation_fee": 1000, "medicines": 2000},
    }


@pytest.fixture
def tc008_payload():
    """TC008: Fraud Detection - Manual Review"""
    return {
        "member_id": "EMP008",
        "member_name": "Ravi Menon",
        "treatment_date": "2024-10-30",
        "claim_amount": 4800,
        "previous_claims_same_day": 3,
        "extracted_data": {
            "patient_name": "Ravi Menon",
            "doctor_name": "Dr. Khan",
            "doctor_registration": "UP/45678/2016",
            "diagnosis": "Migraine",
            "medicines": ["Sumatriptan", "Propranolol"],
            "treatment_date": "2024-10-30",
            "bill_items": {"consultation_fee": 2000, "medicines": 2800},
            "extraction_confidence": 0.92,
        },
        "bill_items": {"consultation_fee": 2000, "medicines": 2800},
    }


# ── UNIT TESTS ───────────────────────────────────────────────────

def test_tc001_approved(client, tc001_payload):
    """Test TC001: approved with standard 10% consultation copay."""
    # Mocking Gemini Medical Necessity Agent call
    with patch("app.agents.medical_necessity_agent.MedicalNecessityAgent.process") as mock_necessity:
        mock_necessity.return_value = MedicalNecessityResult(
            medically_necessary=True, reasoning="Standard consultation", confidence=0.95
        )

        response = client.post("/api/v1/claims/process", json=tc001_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "APPROVED"
        assert data["approved_amount"] == 1350.0
        assert "copay" in data["deductions"]
        assert data["deductions"]["copay"] == 150.0
        assert len(data["trace_summary"]) > 0


def test_tc002_partial_approval(client, tc002_payload):
    """Test TC002: root canal is approved, teeth whitening is rejected (cosmetic)."""
    with patch("app.agents.medical_necessity_agent.MedicalNecessityAgent.process") as mock_necessity:
        mock_necessity.return_value = MedicalNecessityResult(
            medically_necessary=True, reasoning="Root canal required", confidence=0.95
        )

        response = client.post("/api/v1/claims/process", json=tc002_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "PARTIAL"
        assert data["approved_amount"] == 8000.0
        assert len(data["rejected_items"]) == 1
        assert "Teeth Whitening" in data["rejected_items"][0]


def test_tc005_waiting_period_rejected(client, tc005_payload):
    """Test TC005: diabetes treatment is within 90-day waiting period, must reject."""
    response = client.post("/api/v1/claims/process", json=tc005_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "REJECTED"
    assert "WAITING_PERIOD" in data["rejection_reasons"]
    assert data["approved_amount"] == 0.0


def test_tc008_fraud_manual_review(client, tc008_payload):
    """Test TC008: multiple claims same day trigger low pipeline confidence and refer to manual review."""
    with patch("app.agents.medical_necessity_agent.MedicalNecessityAgent.process") as mock_necessity:
        mock_necessity.return_value = MedicalNecessityResult(
            medically_necessary=True, reasoning="Standard migraine consultation", confidence=0.95
        )

        response = client.post("/api/v1/claims/process", json=tc008_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["decision"] == "MANUAL_REVIEW"
        assert data["confidence_score"] == 0.65


# ── FILE UPLOAD AND INTEGRATION TESTING ─────────────────────────

def test_claims_upload_endpoint(client):
    """Test the /claims/upload multipart-form endpoint by mocking document extraction."""
    # Create mock text files representing attachments
    files = [
        ("files", ("prescription.jpg", b"mocked prescription image data", "image/jpeg")),
        ("files", ("invoice.png", b"mocked medical invoice image data", "image/png")),
    ]
    form_data = {
        "member_id": "EMP001",
        "claim_amount": 1500,
        "treatment_date": "2024-11-01",
        "hospital_name": "Apollo Hospitals",
        "is_cashless": True,
    }

    # Mock extraction and necessity checks
    with patch("app.agents.extraction_agent.MultimodalExtractionAgent.process") as mock_extract, \
         patch("app.agents.medical_necessity_agent.MedicalNecessityAgent.process") as mock_necessity:
        
        mock_extract.return_value = ExtractedData(
            patient_name="Rajesh Kumar",
            doctor_name="Dr. Sharma",
            doctor_registration="KA/45678/2015",
            diagnosis="Viral fever",
            medicines=["Paracetamol 650mg"],
            treatment_date=date(2024, 11, 1),
            provider_name="Apollo Hospitals",
            bill_amount=1500.0,
            bill_items={"consultation_fee": 1000, "diagnostic_tests": 500},
            extraction_confidence=0.95,
        )
        mock_necessity.return_value = MedicalNecessityResult(
            medically_necessary=True, reasoning="Valid clinical findings", confidence=0.95
        )

        response = client.post("/api/v1/claims/upload", data=form_data, files=files)
        assert response.status_code == 200
        data = response.json()
        
        # Cashless at Apollo (network hospital) gets 20% network discount (Rs 300)
        # 1500 - 300 = 1200
        assert data["decision"] == "APPROVED"
        assert data["approved_amount"] == 1200.0
        assert data["is_cashless_approved"] is True
        assert data["network_discount"] == 300.0

        # Now check if we can query get_claim_status for this claim
        claim_id = data["claim_id"]
        status_response = client.get(f"/api/v1/claims/{claim_id}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["claim_id"] == claim_id
        assert status_data["decision"] == "APPROVED"
        assert len(status_data["trace_ledger"]) > 0
        assert "investigator_report" in status_data
        assert status_data["investigator_report"]["claim_summary"]["claim_id"] == claim_id
