import pytest
from datetime import date

# Import test cases from run_tests runner
from run_tests import test_cases

def test_api_integration_all_test_cases(client):
    """
    Test the FastAPI /claims/process endpoint for all 10 standard test cases (TC001–TC010).
    Verifies that API request/response flows work correctly and match expectations.
    """
    for case in test_cases:
        payload = case["payload"].copy()
        
        # Format date as string for JSON serialization
        if isinstance(payload.get("treatment_date"), date):
            payload["treatment_date"] = payload["treatment_date"].isoformat()
        if "extracted_data" in payload and isinstance(payload["extracted_data"].get("treatment_date"), date):
            payload["extracted_data"]["treatment_date"] = payload["extracted_data"]["treatment_date"].isoformat()
        if isinstance(payload.get("member_join_date"), date):
            payload["member_join_date"] = payload["member_join_date"].isoformat()

        response = client.post("/api/v1/claims/process", json=payload)
        assert response.status_code == 200, f"Failed on {case['id']}: {response.text}"
        data = response.json()

        assert data["decision"] == case["expected_decision"], f"Decision mismatch on {case['id']}: got {data['decision']}, expected {case['expected_decision']}"
        assert data["approved_amount"] == case["expected_amount"], f"Amount mismatch on {case['id']}: got {data['approved_amount']}, expected {case['expected_amount']}"
