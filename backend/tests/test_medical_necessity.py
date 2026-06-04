import pytest
from unittest.mock import patch
from app.agents.medical_necessity_agent import MedicalNecessityAgent
from app.schemas.claim_schema import ExtractedData

def test_necessity_agent_no_api_key():
    with patch.dict("os.environ", {}, clear=True):
        agent = MedicalNecessityAgent()
        result = agent.process(ExtractedData(diagnosis="Viral fever"))
        
        assert result.medically_necessary is True
        assert "not configured" in result.reasoning
        assert result.confidence == 1.0

def test_necessity_agent_success():
    with patch.dict("os.environ", {"GEMINI_API_KEY": "AIzaSyMockKey"}):
        agent = MedicalNecessityAgent()
        
        mock_response = '{"medically_necessary": true, "reasoning": "Paracetamol aligns with Viral fever diagnosis.", "confidence": 0.95}'
        with patch.object(agent, "_call_gemini", return_value=mock_response):
            result = agent.process(ExtractedData(
                diagnosis="Viral fever",
                medicines=["Paracetamol 650mg"],
                tests=["CBC"]
            ))
            
            assert result.medically_necessary is True
            assert "Paracetamol aligns" in result.reasoning
            assert result.confidence == 0.95

def test_necessity_agent_failure_fallback():
    with patch.dict("os.environ", {"GEMINI_API_KEY": "AIzaSyMockKey"}):
        agent = MedicalNecessityAgent()
        
        with patch.object(agent, "_call_gemini", side_effect=Exception("API Error")):
            result = agent.process(ExtractedData(diagnosis="Viral fever"))
            
            assert result.medically_necessary is True
            assert "Error evaluating necessity" in result.reasoning
            assert result.confidence == 0.5
