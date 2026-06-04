"""Quick test runner for all 10 test cases against the running server."""
import requests
import json
import sys

BASE = "http://localhost:8001/api/v1/claims/process"

test_cases = [
    {
        "id": "TC001",
        "name": "Simple Consultation - Approved",
        "payload": {
            "member_id": "EMP001",
            "member_name": "Rajesh Kumar",
            "treatment_date": "2024-11-01",
            "claim_amount": 1500,
            "documents_submitted": ["prescription", "bill"],
            "extracted_data": {
                "patient_name": "Rajesh Kumar",
                "doctor_name": "Dr. Sharma",
                "doctor_registration": "KA/45678/2015",
                "diagnosis": "Viral fever",
                "medicines": ["Paracetamol 650mg", "Vitamin C"],
                "procedures": [],
                "tests": ["CBC", "Dengue test"],
                "bill_amount": 1500,
                "treatment_date": "2024-11-01",
            },
            "bill_items": {"consultation_fee": 1000, "diagnostic_tests": 500},
        },
        "expected_decision": "APPROVED",
        "expected_amount": 1350,
    },
    {
        "id": "TC002",
        "name": "Dental Treatment - Partial Approval",
        "payload": {
            "member_id": "EMP002",
            "member_name": "Priya Singh",
            "treatment_date": "2024-10-15",
            "claim_amount": 12000,
            "documents_submitted": ["prescription", "bill"],
            "extracted_data": {
                "patient_name": "Priya Singh",
                "doctor_name": "Dr. Patel",
                "doctor_registration": "MH/23456/2018",
                "diagnosis": "Tooth decay requiring root canal",
                "procedures": ["Root canal treatment", "Teeth whitening"],
                "medicines": [],
                "tests": [],
                "bill_amount": 12000,
                "treatment_date": "2024-10-15",
            },
            "bill_items": {"root_canal": 8000, "teeth_whitening": 4000},
        },
        "expected_decision": "PARTIAL",
        "expected_amount": 8000,
    },
    {
        "id": "TC003",
        "name": "Limit Exceeded - Rejected",
        "payload": {
            "member_id": "EMP003",
            "member_name": "Amit Verma",
            "treatment_date": "2024-10-20",
            "claim_amount": 7500,
            "documents_submitted": ["prescription", "bill"],
            "extracted_data": {
                "patient_name": "Amit Verma",
                "doctor_name": "Dr. Gupta",
                "doctor_registration": "DL/34567/2016",
                "diagnosis": "Gastroenteritis",
                "medicines": ["Antibiotics", "Probiotics"],
                "procedures": [],
                "tests": [],
                "bill_amount": 7500,
                "treatment_date": "2024-10-20",
            },
            "bill_items": {"consultation_fee": 2000, "medicines": 5500},
        },
        "expected_decision": "REJECTED",
        "expected_amount": 0,
    },
    {
        "id": "TC004",
        "name": "Missing Documents - Rejected",
        "payload": {
            "member_id": "EMP004",
            "member_name": "Sneha Reddy",
            "treatment_date": "2024-10-25",
            "claim_amount": 2000,
            "documents_submitted": ["bill"],
            "extracted_data": {
                "patient_name": "Sneha Reddy",
                "doctor_name": None,
                "doctor_registration": None,
                "diagnosis": None,
                "medicines": [],
                "procedures": [],
                "tests": [],
                "bill_amount": 2000,
                "treatment_date": "2024-10-25",
            },
            "bill_items": {"consultation_fee": 1500, "medicines": 500},
        },
        "expected_decision": "REJECTED",
        "expected_amount": 0,
    },
    {
        "id": "TC005",
        "name": "Pre-existing Condition - Waiting Period",
        "payload": {
            "member_id": "EMP005",
            "member_name": "Vikram Joshi",
            "member_join_date": "2024-09-01",
            "treatment_date": "2024-10-15",
            "claim_amount": 3000,
            "documents_submitted": ["prescription", "bill"],
            "extracted_data": {
                "patient_name": "Vikram Joshi",
                "doctor_name": "Dr. Mehta",
                "doctor_registration": "GJ/56789/2014",
                "diagnosis": "Type 2 Diabetes",
                "medicines": ["Metformin", "Glimepiride"],
                "procedures": [],
                "tests": [],
                "bill_amount": 3000,
                "treatment_date": "2024-10-15",
            },
            "bill_items": {"consultation_fee": 1000, "medicines": 2000},
        },
        "expected_decision": "REJECTED",
        "expected_amount": 0,
    },
    {
        "id": "TC006",
        "name": "Alternative Medicine - Approved",
        "payload": {
            "member_id": "EMP006",
            "member_name": "Kavita Nair",
            "treatment_date": "2024-10-28",
            "claim_amount": 4000,
            "documents_submitted": ["prescription", "bill"],
            "extracted_data": {
                "patient_name": "Kavita Nair",
                "doctor_name": "Vaidya Krishnan",
                "doctor_registration": "AYUR/KL/2345/2019",
                "diagnosis": "Chronic joint pain",
                "medicines": [],
                "procedures": ["Panchakarma therapy"],
                "tests": [],
                "bill_amount": 4000,
                "treatment_date": "2024-10-28",
            },
            "bill_items": {"consultation_fee": 1000, "therapy_charges": 3000},
        },
        "expected_decision": "APPROVED",
        "expected_amount": 4000,
    },
    {
        "id": "TC007",
        "name": "Diagnostic Tests - Pre-auth Required",
        "payload": {
            "member_id": "EMP007",
            "member_name": "Suresh Patil",
            "treatment_date": "2024-11-02",
            "claim_amount": 15000,
            "documents_submitted": ["prescription", "bill"],
            "extracted_data": {
                "patient_name": "Suresh Patil",
                "doctor_name": "Dr. Rao",
                "doctor_registration": "AP/67890/2017",
                "diagnosis": "Suspected lumbar disc herniation",
                "medicines": [],
                "procedures": [],
                "tests": ["MRI Lumbar Spine"],
                "bill_amount": 15000,
                "treatment_date": "2024-11-02",
            },
            "bill_items": {"mri_scan": 15000},
        },
        "expected_decision": "REJECTED",
        "expected_amount": 0,
    },
    {
        "id": "TC008",
        "name": "Fraud Detection - Manual Review",
        "payload": {
            "member_id": "EMP008",
            "member_name": "Ravi Menon",
            "treatment_date": "2024-10-30",
            "claim_amount": 4800,
            "previous_claims_same_day": 3,
            "documents_submitted": ["prescription", "bill"],
            "extracted_data": {
                "patient_name": "Ravi Menon",
                "doctor_name": "Dr. Khan",
                "doctor_registration": "UP/45678/2016",
                "diagnosis": "Migraine",
                "medicines": ["Sumatriptan", "Propranolol"],
                "procedures": [],
                "tests": [],
                "bill_amount": 4800,
                "treatment_date": "2024-10-30",
            },
            "bill_items": {"consultation_fee": 2000, "medicines": 2800},
        },
        "expected_decision": "MANUAL_REVIEW",
        "expected_amount": None,
    },
    {
        "id": "TC009",
        "name": "Excluded Treatment - Rejected",
        "payload": {
            "member_id": "EMP009",
            "member_name": "Anita Desai",
            "treatment_date": "2024-10-18",
            "claim_amount": 8000,
            "documents_submitted": ["prescription", "bill"],
            "extracted_data": {
                "patient_name": "Anita Desai",
                "doctor_name": "Dr. Banerjee",
                "doctor_registration": "WB/34567/2015",
                "diagnosis": "Obesity - BMI 35",
                "medicines": [],
                "procedures": ["Bariatric consultation and diet plan"],
                "tests": [],
                "bill_amount": 8000,
                "treatment_date": "2024-10-18",
            },
            "bill_items": {"consultation_fee": 3000, "diet_plan": 5000},
        },
        "expected_decision": "REJECTED",
        "expected_amount": 0,
    },
    {
        "id": "TC010",
        "name": "Network Hospital - Cashless Approved",
        "payload": {
            "member_id": "EMP010",
            "member_name": "Deepak Shah",
            "treatment_date": "2024-11-03",
            "claim_amount": 4500,
            "hospital_name": "Apollo Hospitals",
            "is_cashless": True,
            "documents_submitted": ["prescription", "bill"],
            "extracted_data": {
                "patient_name": "Deepak Shah",
                "doctor_name": "Dr. Iyer",
                "doctor_registration": "TN/56789/2013",
                "diagnosis": "Acute bronchitis",
                "medicines": ["Antibiotics", "Bronchodilators"],
                "procedures": [],
                "tests": [],
                "bill_amount": 4500,
                "treatment_date": "2024-11-03",
            },
            "bill_items": {"consultation_fee": 1500, "medicines": 3000},
        },
        "expected_decision": "APPROVED",
        "expected_amount": 3600,
    },
]

if __name__ == "__main__":
    passed = 0
    failed = 0
    errors = 0

    for tc in test_cases:
        print(f"\n{'='*60}")
        print(f"  {tc['id']}: {tc['name']}")
        print(f"{'='*60}")
        try:
            r = requests.post(BASE, json=tc["payload"], timeout=10)
            if r.status_code != 200:
                print(f"  HTTP Error: {r.status_code}")
                print(f"  Response: {r.text[:500]}")
                errors += 1
                continue

            result = r.json()
            decision = result.get("decision")
            amount = result.get("approved_amount", 0)
            confidence = result.get("confidence_score", 0)
            fraud_score = result.get("fraud_score", 0)
            rejection = result.get("rejection_reasons", [])
            notes = result.get("notes", "")

            decision_ok = decision == tc["expected_decision"]
            amount_ok = tc["expected_amount"] is None or abs(amount - tc["expected_amount"]) < 1

            status_str = "PASS" if (decision_ok and amount_ok) else "FAIL"
            if status_str == "PASS":
                passed += 1
            else:
                failed += 1

            print(f"  Result: {status_str}")
            print(f"  Decision:  got={decision}  expected={tc['expected_decision']}  {'OK' if decision_ok else 'MISMATCH'}")
            if tc["expected_amount"] is not None:
                print(f"  Amount:    got={amount}  expected={tc['expected_amount']}  {'OK' if amount_ok else 'MISMATCH'}")
            print(f"  Confidence: {confidence}")
            print(f"  Fraud Score: {fraud_score}")
            if rejection:
                print(f"  Rejection Reasons: {rejection}")
            if notes:
                print(f"  Notes: {notes[:200]}")

        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1

    print(f"\n{'='*60}")
    print(f"  SUMMARY: {passed} passed, {failed} failed, {errors} errors out of {len(test_cases)} tests")
    print(f"{'='*60}")
