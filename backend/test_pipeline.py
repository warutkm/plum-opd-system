"""
Plum OPD Claim Adjudication System — Pipeline Smoke Test
=========================================================
Runs all 10 test cases through the full ClaimPipeline orchestrator.
Verifies decisions, approved amounts, fraud flags, and trace ledger logging.
"""

import json
import sys
from datetime import date
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.engine.rule_engine import DeterministicRuleEngine
from app.services.claim_service import ClaimService
from app.models.domain import ExtractedData, Member, PolicyTerms


def load_policy() -> PolicyTerms:
    p = Path(__file__).parent / "reference" / "policy_terms.json"
    if not p.exists():
        p = Path(__file__).parent.parent / "reference" / "policy_terms.json"
    return PolicyTerms(**json.loads(p.read_text()))


def run_tests():
    policy = load_policy()
    engine = DeterministicRuleEngine(policy)
    pipeline = ClaimService(policy)

    passed = 0
    failed = 0

    print("🏁 Starting Master Pipeline Smoke Test (10 Test Cases) ...\n")

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
    ok = r.decision == "APPROVED" and r.approved_amount == 1350.0
    print(
        f"{'✅' if ok else '❌'} TC001  decision={r.decision}  amt={r.approved_amount}  (expect APPROVED / 1350)"
    )
    passed += ok
    failed += not ok

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
    ok = r.decision == "PARTIAL" and r.approved_amount == 8000.0
    print(
        f"{'✅' if ok else '❌'} TC002  decision={r.decision}  amt={r.approved_amount}  (expect PARTIAL / 8000)"
    )
    passed += ok
    failed += not ok

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
    ok = r.decision == "REJECTED" and "PER_CLAIM_EXCEEDED" in r.rejection_reasons
    print(
        f"{'✅' if ok else '❌'} TC003  decision={r.decision}  reasons={r.rejection_reasons}  (expect REJECTED / PER_CLAIM_EXCEEDED)"
    )
    passed += ok
    failed += not ok

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
    ok = r.decision == "REJECTED" and "MISSING_DOCUMENTS" in r.rejection_reasons
    print(
        f"{'✅' if ok else '❌'} TC004  decision={r.decision}  reasons={r.rejection_reasons}  (expect REJECTED / MISSING_DOCUMENTS)"
    )
    passed += ok
    failed += not ok

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
    ok = r.decision == "REJECTED" and "WAITING_PERIOD" in r.rejection_reasons
    print(
        f"{'✅' if ok else '❌'} TC005  decision={r.decision}  reasons={r.rejection_reasons}  (expect REJECTED / WAITING_PERIOD)"
    )
    passed += ok
    failed += not ok

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
    ok = r.decision == "APPROVED" and r.approved_amount == 4000.0
    print(
        f"{'✅' if ok else '❌'} TC006  decision={r.decision}  amt={r.approved_amount}  (expect APPROVED / 4000)"
    )
    passed += ok
    failed += not ok

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
    ok = r.decision == "REJECTED" and "PRE_AUTH_MISSING" in r.rejection_reasons
    print(
        f"{'✅' if ok else '❌'} TC007  decision={r.decision}  reasons={r.rejection_reasons}  (expect REJECTED / PRE_AUTH_MISSING)"
    )
    passed += ok
    failed += not ok

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
    # The aggregated decision is MANUAL_REVIEW due to suspicious frequency (capping confidence at 0.65)
    ok = r.decision == "MANUAL_REVIEW" and r.confidence_score == 0.65
    print(
        f"{'✅' if ok else '❌'} TC008  decision={r.decision}  confidence={r.confidence_score}  (expect MANUAL_REVIEW / 0.65)"
    )
    passed += ok
    failed += not ok

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
    ok = r.decision == "REJECTED" and "SERVICE_NOT_COVERED" in r.rejection_reasons
    print(
        f"{'✅' if ok else '❌'} TC009  decision={r.decision}  reasons={r.rejection_reasons}  (expect REJECTED / SERVICE_NOT_COVERED)"
    )
    passed += ok
    failed += not ok

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
    ok = r.decision == "APPROVED" and r.approved_amount == 3600.0 and r.is_cashless_approved
    print(
        f"{'✅' if ok else '❌'} TC010  decision={r.decision}  amt={r.approved_amount}  cashless={r.is_cashless_approved}  (expect APPROVED / 3600 / cashless)"
    )
    passed += ok
    failed += not ok

    # ── Verify Trace Ledger ────────────────────────────────────
    print("\n🔍 Verifying Trace Ledger Step Count ...")
    # There should be trace entries for all stages
    stages_found = [t.step for t in r.trace_summary]
    print(f"   Traces generated: {stages_found}")
    trace_ok = len(r.trace_summary) >= 8
    print(f"{'✅' if trace_ok else '❌'} Trace ledger verification")

    # ── Summary ─────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Results:  {passed} passed  /  {failed} failed  /  {passed+failed} total")
    print(f"{'='*60}")
    return failed == 0 and trace_ok


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
