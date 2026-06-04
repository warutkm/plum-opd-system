import json
import pytest
from pathlib import Path
from app.models.policy import PolicyTerms

@pytest.fixture(autouse=True)
def clean_in_memory_claims():
    """Autouse fixture to clear in-memory claims store before each test to isolate state."""
    from app.database import IN_MEMORY_CLAIMS
    IN_MEMORY_CLAIMS.clear()

@pytest.fixture
def base_policy():
    p = Path(__file__).parent / "reference" / "policy_terms.json"
    if not p.exists():
        p = Path(__file__).parent.parent / "reference" / "policy_terms.json"
    
    data = json.loads(p.read_text())
    
    # Adjust for test requirements
    data["policy_id"] = "POL_OPD_ADVANTAGE"
    data["coverage_details"]["annual_limit"] = 15000.0
    data["coverage_details"]["consultation_fees"]["sub_limit"] = 5000.0
    
    # Make sure specific diagnostic tests are covered if they are checked
    if "MRI Lumbar Spine (with pre-auth)" not in data["coverage_details"]["diagnostic_tests"]["covered_tests"]:
        data["coverage_details"]["diagnostic_tests"]["covered_tests"].append("MRI Lumbar Spine (with pre-auth)")
    
    return PolicyTerms(**data)


@pytest.fixture
def client():
    """Fixture to provide a test client with FastAPI lifespan started/stopped."""
    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app) as c:
        yield c
