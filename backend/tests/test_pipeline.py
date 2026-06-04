import json
from datetime import date
from pathlib import Path
from app.engine.rule_engine import DeterministicRuleEngine
from app.services.claim_service import ClaimService
from app.models.domain import ExtractedData, Member, PolicyTerms

def load_policy() -> PolicyTerms:
    p = Path(__file__).parent / "sample_data" / "test_policy.json"
    if not p.exists():
        p = Path(__file__).parent.parent / "reference" / "policy_terms.json"
    return PolicyTerms(**json.loads(p.read_text()))

def test_full_pipeline_smoke_all_cases():
    policy = load_policy()
    pipeline = ClaimService(policy)

    # ── TC001: Simple Consultation — Approved ──────────────────
    member = Member(
        member_id="EMP001",
        name="Rajesh Kumar",
        join_date=date(2024, 1, 1),
        policy_id=policy.policy_id,
    )
    r = pipeline.process_claim(
        member=member,
        claim_amount=1500,
        treatment_date=date(2024, 11, 1),
        pre_extracted_data=ExtractedData(
            patient_name="Rajesh Kumar",
            doctor_name="Dr. Sharma",
            doctor_registration="KA/45678/2015",
            diagnosis="Viral fever",
            medicines=["Paracetamol 650mg", "Vitamin C"],
            tests=["CBC", "Dengue test"],
            treatment_date=date(2024, 11, 1),
            extraction_confidence=0.92,
        ),
        pre_bill_items={"consultation_fee": 1000, "diagnostic_tests": 500},
    )
    assert r.decision == "APPROVED"
    assert r.approved_amount == 1350.0

    # ── TC002: Dental — Partial ────────────────────────────────
    member = Member(
        member_id="EMP002",
        name="Priya Singh",
        join_date=date(2024, 1, 1),
        policy_id=policy.policy_id,
    )
    r = pipeline.process_claim(
        member=member,
        claim_amount=12000,
        treatment_date=date(2024, 10, 15),
        pre_extracted_data=ExtractedData(
            patient_name="Priya Singh",
            doctor_name="Dr. Patel",
            doctor_registration="MH/23456/2018",
            diagnosis="Tooth decay requiring root canal",
            procedures=["Root canal treatment", "Teeth whitening"],
            treatment_date=date(2024, 10, 15),
            extraction_confidence=0.92,
        ),
        pre_bill_items={"root_canal": 8000, "teeth_whitening": 4000},
    )
    assert r.decision == "PARTIAL"
    assert r.approved_amount == 8000.0

    # ── TC003: Limit Exceeded — Rejected ───────────────────────
    member = Member(
        member_id="EMP003",
        name="Amit Verma",
        join_date=date(2024, 1, 1),
        policy_id=policy.policy_id,
    )
    r = pipeline.process_claim(
        member=member,
        claim_amount=7500,
        treatment_date=date(2024, 10, 20),
        pre_extracted_data=ExtractedData(
            patient_name="Amit Verma",
            doctor_name="Dr. Gupta",
            doctor_registration="DL/34567/2016",
            diagnosis="Gastroenteritis",
            medicines=["Antibiotics", "Probiotics"],
            treatment_date=date(2024, 10, 20),
            extraction_confidence=0.92,
        ),
        pre_bill_items={"consultation_fee": 2000, "medicines": 5500},
    )
    assert r.decision == "REJECTED"
    assert "PER_CLAIM_EXCEEDED" in r.rejection_reasons

    # ── TC004: Missing Documents — Rejected ────────────────────
    member = Member(
        member_id="EMP004",
        name="Sneha Reddy",
        join_date=date(2024, 1, 1),
        policy_id=policy.policy_id,
    )
    r = pipeline.process_claim(
        member=member,
        claim_amount=2000,
        treatment_date=date(2024, 10, 25),
        pre_extracted_data=ExtractedData(
            patient_name="Sneha Reddy",
            treatment_date=date(2024, 10, 25),
            extraction_confidence=0.92,
        ),
        pre_bill_items={"consultation_fee": 1500, "medicines": 500},
    )
    assert r.decision == "REJECTED"
    assert "MISSING_DOCUMENTS" in r.rejection_reasons

    # ── TC005: Waiting Period — Rejected ───────────────────────
    member = Member(
        member_id="EMP005",
        name="Vikram Joshi",
        join_date=date(2024, 9, 1),
        policy_id=policy.policy_id,
    )
    r = pipeline.process_claim(
        member=member,
        claim_amount=3000,
        treatment_date=date(2024, 10, 15),
        pre_extracted_data=ExtractedData(
            patient_name="Vikram Joshi",
            doctor_name="Dr. Mehta",
            doctor_registration="GJ/56789/2014",
            diagnosis="Type 2 Diabetes",
            medicines=["Metformin", "Glimepiride"],
            treatment_date=date(2024, 10, 15),
            extraction_confidence=0.92,
        ),
        pre_bill_items={"consultation_fee": 1000, "medicines": 2000},
    )
    assert r.decision == "REJECTED"
    assert "WAITING_PERIOD" in r.rejection_reasons

    # ── TC006: Alternative Medicine — Approved ─────────────────
    member = Member(
        member_id="EMP006",
        name="Kavita Nair",
        join_date=date(2024, 1, 1),
        policy_id=policy.policy_id,
    )
    r = pipeline.process_claim(
        member=member,
        claim_amount=4000,
        treatment_date=date(2024, 10, 28),
        pre_extracted_data=ExtractedData(
            patient_name="Kavita Nair",
            doctor_name="Vaidya Krishnan",
            doctor_registration="AYUR/KL/2345/2019",
            diagnosis="Chronic joint pain",
            procedures=["Panchakarma therapy"],
            treatment_date=date(2024, 10, 28),
            extraction_confidence=0.92,
        ),
        pre_bill_items={"consultation_fee": 1000, "therapy_charges": 3000},
    )
    assert r.decision == "APPROVED"
    assert r.approved_amount == 4000.0

    # ── TC007: Pre-Auth Required — Rejected ────────────────────
    member = Member(
        member_id="EMP007",
        name="Suresh Patil",
        join_date=date(2024, 1, 1),
        policy_id=policy.policy_id,
    )
    r = pipeline.process_claim(
        member=member,
        claim_amount=15000,
        treatment_date=date(2024, 11, 2),
        pre_extracted_data=ExtractedData(
            patient_name="Suresh Patil",
            doctor_name="Dr. Rao",
            doctor_registration="AP/67890/2017",
            diagnosis="Suspected lumbar disc herniation",
            tests=["MRI Lumbar Spine"],
            treatment_date=date(2024, 11, 2),
            extraction_confidence=0.92,
        ),
        pre_bill_items={"mri_scan": 15000},
        has_pre_auth=False,
    )
    assert r.decision == "REJECTED"
    assert "PRE_AUTH_MISSING" in r.rejection_reasons

    # ── TC008: Fraud Detection — Referred for Manual Review ─────
    member = Member(
        member_id="EMP008",
        name="Ravi Menon",
        join_date=date(2024, 1, 1),
        policy_id=policy.policy_id,
    )
    r = pipeline.process_claim(
        member=member,
        claim_amount=4800,
        treatment_date=date(2024, 10, 30),
        pre_extracted_data=ExtractedData(
            patient_name="Ravi Menon",
            doctor_name="Dr. Khan",
            doctor_registration="UP/45678/2016",
            diagnosis="Migraine",
            medicines=["Sumatriptan", "Propranolol"],
            treatment_date=date(2024, 10, 30),
            extraction_confidence=0.92,
        ),
        pre_bill_items={"consultation_fee": 2000, "medicines": 2800},
        previous_claims_same_day=3,
    )
    assert r.decision == "MANUAL_REVIEW"
    assert r.confidence_score == 0.65

    # ── TC009: Excluded Treatment — Rejected ───────────────────
    member = Member(
        member_id="EMP009",
        name="Anita Desai",
        join_date=date(2024, 1, 1),
        policy_id=policy.policy_id,
    )
    r = pipeline.process_claim(
        member=member,
        claim_amount=8000,
        treatment_date=date(2024, 10, 18),
        pre_extracted_data=ExtractedData(
            patient_name="Anita Desai",
            doctor_name="Dr. Banerjee",
            doctor_registration="WB/34567/2015",
            diagnosis="Obesity - BMI 35",
            procedures=["Bariatric consultation and diet plan"],
            treatment_date=date(2024, 10, 18),
            extraction_confidence=0.92,
        ),
        pre_bill_items={"consultation_fee": 3000, "diet_plan": 5000},
    )
    assert r.decision == "REJECTED"
    assert "SERVICE_NOT_COVERED" in r.rejection_reasons

    # ── TC010: Network Hospital — Approved with discount ───────
    member = Member(
        member_id="EMP010",
        name="Deepak Shah",
        join_date=date(2024, 1, 1),
        policy_id=policy.policy_id,
    )
    r = pipeline.process_claim(
        member=member,
        claim_amount=4500,
        treatment_date=date(2024, 11, 3),
        pre_extracted_data=ExtractedData(
            patient_name="Deepak Shah",
            doctor_name="Dr. Iyer",
            doctor_registration="TN/56789/2013",
            diagnosis="Acute bronchitis",
            medicines=["Antibiotics", "Bronchodilators"],
            treatment_date=date(2024, 11, 3),
            extraction_confidence=0.92,
        ),
        pre_bill_items={"consultation_fee": 1500, "medicines": 3000},
        hospital_name="Apollo Hospitals",
        is_cashless=True,
    )
    assert r.decision == "APPROVED"
    assert r.approved_amount == 3600.0
    assert r.is_cashless_approved is True
