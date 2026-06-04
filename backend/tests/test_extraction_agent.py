import pytest
from unittest.mock import patch, MagicMock
from app.agents.extraction_agent import MultimodalExtractionAgent

def test_extraction_no_api_key():
    with patch.dict("os.environ", {}, clear=True):
        agent = MultimodalExtractionAgent()
        result = agent.process([(b"mock_bytes", "image/png")])
        
        assert result.extraction_confidence == 0.0
        assert "error" in result.raw_extraction
        assert "not configured" in result.raw_extraction["error"]

def test_extraction_empty_files():
    with patch.dict("os.environ", {"GEMINI_API_KEY": "AIzaSyMockKey"}):
        agent = MultimodalExtractionAgent()
        result = agent.process([])
        
        assert result.extraction_confidence == 0.0
        assert "error" in result.raw_extraction
        assert "No files" in result.raw_extraction["error"]

def test_extraction_success():
    with patch.dict("os.environ", {"GEMINI_API_KEY": "AIzaSyMockKey"}):
        agent = MultimodalExtractionAgent()
        
        mock_json = """{
            "patient_name": "Rajesh Kumar",
            "bill_number": "INV-2025-001",
            "age": "35",
            "doctor_name": "Dr. Anita Sharma",
            "doctor_registration": "KA/45678/2015",
            "diagnosis": "Acute Pharyngitis",
            "medicines": [],
            "procedures": ["Consultation"],
            "tests": [],
            "provider_name": "Apollo Hospitals",
            "bill_amount": 1500.0,
            "treatment_date": "2025-03-15",
            "bill_items": {"consultation_fee": 1500.0},
            "extraction_confidence": 0.95
        }"""
        
        with patch.object(agent, "_call_gemini", return_value=mock_json):
            result = agent.process([(b"mock_bytes", "image/png")])
            
            assert result.patient_name == "Rajesh Kumar"
            assert result.doctor_registration == "KA/45678/2015"
            assert result.bill_amount == 1500.0
            assert result.treatment_date.isoformat() == "2025-03-15"
            assert result.extraction_confidence > 0.80

def test_extraction_invalid_json():
    with patch.dict("os.environ", {"GEMINI_API_KEY": "AIzaSyMockKey"}):
        agent = MultimodalExtractionAgent()
        
        with patch.object(agent, "_call_gemini", return_value="Invalid JSON Response"):
            result = agent.process([(b"mock_bytes", "image/png")])
            
            assert result.extraction_confidence == 0.0
            assert "error" in result.raw_extraction
            assert "JSON parse error" in result.raw_extraction["error"]
