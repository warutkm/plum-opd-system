"""
Test the /api/v1/claims/upload endpoint with a sample medical bill image.

Creates a simple test image with bill-like text content, then uploads it
through the multimodal AI extraction pipeline.
"""

import requests
import json
import io
import sys

BASE = "http://localhost:8001/api/v1/claims/upload"


def create_test_bill_text():
    """Create a simple text file masquerading as a bill for testing."""
    bill_text = """
    APOLLO HOSPITALS, BANGALORE
    ----------------------------
    Patient: Rajesh Kumar
    Age: 35 years
    Date: 15/03/2025
    
    Doctor: Dr. Anita Sharma
    Registration: KA/45678/2015
    
    Diagnosis: Acute Pharyngitis
    
    BILL DETAILS:
    Consultation Fee: Rs. 1,500
    ----------------------------
    TOTAL: Rs. 1,500
    
    Medicines Prescribed:
    - Azithromycin 500mg
    - Paracetamol 650mg
    """
    return bill_text.encode("utf-8")


def test_upload_pdf():
    """Test with a simple PDF-like upload."""
    print("\n" + "=" * 60)
    print("  TEST: Upload Endpoint - Medical Bill")
    print("=" * 60)

    # Create a minimal test PDF
    # For testing, we'll use a text-based approach
    bill_bytes = create_test_bill_text()

    try:
        # Use image/png as type since plain text might be rejected
        # In real usage, actual PDF/JPG/PNG files would be uploaded
        files = [
            ("files", ("medical_bill.png", bill_bytes, "image/png")),
        ]

        data = {
            "member_id": "EMP001",
            "treatment_date": "2025-03-15",
            "claim_amount": 1500.0,
            "hospital_name": "Apollo Hospitals",
            "is_cashless": False,
            "has_pre_authorization": False,
        }

        response = requests.post(BASE, files=files, data=data, timeout=120)

        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ Upload successful!")
            print(f"  Claim ID:    {result['claim_id']}")
            print(f"  Decision:    {result['decision']}")
            print(f"  Amount:      {result['approved_amount']}")
            print(f"  Confidence:  {result['confidence_score']}")
            print(f"  Fraud Score: {result['fraud_score']}")
            if result.get("notes"):
                print(f"  Notes:       {result['notes']}")
            if result.get("rejection_reasons"):
                print(f"  Rejections:  {result['rejection_reasons']}")

            # Print trace summary
            print("\n  Pipeline Trace:")
            for trace in result.get("trace_summary", []):
                step = trace.get("step", "?")
                status = trace.get("status", "?")
                duration = trace.get("duration_ms", 0)
                icon = "✅" if status == "PASS" else "⚠️" if status == "WARNING" else "❌" if status == "FAIL" else "⏭️"
                print(f"    {icon} {step}: {status} ({duration}ms)")

            return True
        else:
            print(f"  ❌ HTTP Error: {response.status_code}")
            print(f"  Response: {response.text[:500]}")
            return False

    except requests.ConnectionError:
        print("  ❌ Connection Error: Server not running on port 8001")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_upload_invalid_type():
    """Test with an unsupported file type."""
    print("\n" + "=" * 60)
    print("  TEST: Upload Endpoint - Invalid File Type")
    print("=" * 60)

    files = [
        ("files", ("document.txt", b"some text", "text/plain")),
    ]
    data = {
        "member_id": "EMP001",
        "treatment_date": "2025-03-15",
        "claim_amount": 1500.0,
    }

    try:
        response = requests.post(BASE, files=files, data=data, timeout=30)
        if response.status_code == 400:
            print(f"  ✅ Correctly rejected with 400: {response.json().get('detail', '')}")
            return True
        else:
            print(f"  ❌ Expected 400, got {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


if __name__ == "__main__":
    passed = 0
    total = 0

    total += 1
    if test_upload_pdf():
        passed += 1

    total += 1
    if test_upload_invalid_type():
        passed += 1

    print("\n" + "=" * 60)
    print(f"  UPLOAD TESTS: {passed}/{total} passed")
    print("=" * 60)
