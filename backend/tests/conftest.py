import json
import pytest
from pathlib import Path
from app.models.policy import PolicyTerms

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
