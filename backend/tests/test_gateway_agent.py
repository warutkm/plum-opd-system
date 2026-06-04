import pytest
from app.agents.gateway_agent import GatewayAgent

def test_gateway_agent_success():
    agent = GatewayAgent()
    status, claim_id, details, trace = agent.process(file_contents=None)
    
    assert status == "PASS"
    assert claim_id.startswith("CLM_")
    assert trace.step == "gateway_check"
    assert trace.status == "PASS"

def test_gateway_agent_override():
    agent = GatewayAgent()
    status, claim_id, details, trace = agent.process(file_contents=None, claim_id_override="CLM_MOCK_9999")
    
    assert status == "PASS"
    assert claim_id == "CLM_MOCK_9999"
    assert details["claim_id"] == "CLM_MOCK_9999"

def test_gateway_agent_file_too_large():
    agent = GatewayAgent()
    # Mock a file of 11MB (11 * 1024 * 1024 bytes)
    file_bytes = b"0" * (11 * 1024 * 1024)
    file_contents = [(file_bytes, "application/pdf")]
    
    status, claim_id, details, trace = agent.process(file_contents=file_contents)
    
    assert status == "FAIL"
    assert "exceeds 10MB limit" in details["error"]

def test_gateway_agent_unsupported_mime():
    agent = GatewayAgent()
    file_contents = [(b"mock content", "application/zip")]
    
    status, claim_id, details, trace = agent.process(file_contents=file_contents)
    
    assert status == "FAIL"
    assert "is not supported" in details["error"]
