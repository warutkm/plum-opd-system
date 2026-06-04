# API Documentation

This document describes the API endpoints provided by the Plum OPD Claim Adjudication backend.

- **Base URL**: `http://localhost:8000/api/v1`
- **Default Port**: `8000`

---

## 1. Claims Management

### Submit Claim (Multipart / Upload)
Adjudicates claim documents (prescriptions, invoices, reports) uploaded as files.

- **Endpoint**: `POST /claims/upload`
- **Content-Type**: `multipart/form-data`
- **Request Parameters**:
  - `member_id` (Form Field, String, Required)
  - `claim_amount` (Form Field, Float, Required)
  - `treatment_date` (Form Field, Date string `YYYY-MM-DD`, Required)
  - `hospital_name` (Form Field, String, Optional)
  - `is_cashless` (Form Field, Boolean, Optional, Default: `false`)
  - `files` (File Attachments, List of UploadFiles, Required)

---

### Submit Claim (Direct Process / JSON)
Runs the claim adjudication pipeline directly using pre-extracted or mockup JSON payloads. Useful for deterministic regression testing (TC001–TC010).

- **Endpoint**: `POST /claims/process`
- **Content-Type**: `application/json`
- **Request Schema (`ProcessClaimRequest`)**:
```json
{
  "member_id": "EMP001",
  "member_name": "Rajesh Kumar",
  "treatment_date": "2024-11-01",
  "claim_amount": 1500,
  "hospital_name": "Apollo Hospitals",
  "is_cashless": true,
  "documents_submitted": ["prescription", "bill"],
  "extracted_data": {
    "patient_name": "Rajesh Kumar",
    "doctor_name": "Dr. Sharma",
    "doctor_registration": "KA/45678/2015",
    "diagnosis": "Viral fever",
    "medicines": ["Paracetamol"],
    "procedures": [],
    "tests": ["CBC"]
  },
  "bill_items": {
    "consultation_fee": 1000,
    "diagnostic_tests": 500
  }
}
```

- **Response Schema (`ClaimDecisionOutput`)**:
```json
{
  "claim_id": "CLM_2026_0001",
  "decision": "APPROVED",
  "approved_amount": 1350,
  "rejection_reasons": [],
  "confidence_score": 0.97,
  "fraud_score": 0.0,
  "notes": "Claim approved completely",
  "trace_summary": [
    {
      "step": "gateway_check",
      "status": "PASS",
      "details": {},
      "duration_ms": 12
    }
  ]
}
```

---

### Get Claim Adjudication Status
Retrieves the full decision result, Trace Ledger logs, and the structured Investigator Report for a claim.

- **Endpoint**: `GET /claims/{claim_id}/status`
- **Response**:
```json
{
  "claim_id": "CLM_2026_0001",
  "status": "DECIDED",
  "decision": "APPROVED",
  "approved_amount": 1350,
  "confidence_score": 0.97,
  "fraud_score": 0,
  "trace_ledger": [...],
  "investigator_report": {
    "claim_summary": {},
    "coverage_analysis": {},
    "limit_analysis": {},
    "fraud_analysis": {},
    "decision_rationale": {},
    "what_if_analysis": {},
    "policy_references": []
  }
}
```

---

### List Claims
Lists all claims submitted to the in-memory or database queue. Used to populate the Adjuster Dashboard.

- **Endpoint**: `GET /claims`
- **Response**:
```json
{
  "claims": [
    {
      "claim_id": "CLM_2026_0001",
      "decision": "APPROVED",
      "approved_amount": 1350,
      "confidence_score": 0.97,
      "fraud_score": 0
    }
  ]
}
```

---

## 2. Adjuster Overrides

### Review Flagged Claim
Allows manual adjusters to override claims that are flagged for review.

- **Endpoint**: `PUT /review/{claim_id}`
- **Request Body (`ReviewAction`)**:
```json
{
  "override_decision": "APPROVED",
  "override_amount": 1200.0,
  "adjuster_notes": "Consultation approved after verifying manual copy of registration ID.",
  "adjuster_id": "ADJ_001"
}
```

- **Response**:
```json
{
  "message": "Override applied successfully.",
  "claim_id": "CLM_2026_0001"
}
```

---

## 3. Policy Copilot (RAG)

### Chat with Policy Assistant
Query policy terms and rule eligibility in natural language.

- **Endpoint**: `POST /policy/chat`
- **Request Body (`RAGQuery`)**:
```json
{
  "question": "What is the consultation limit and co-pay rule?",
  "claim_id": "CLM_2026_0001"
}
```

- **Response Body (`RAGResponse`)**:
```json
{
  "answer": "Consultation fees are capped at ₹1500 per claim, and a standard 10% co-pay is deducted.",
  "sources": [
    {
      "chunk_text": "Consultations are capped at ₹1500 per visit...",
      "source": "adjudication_rules.md",
      "similarity": 0.89
    }
  ],
  "confidence": 0.92
}
```
