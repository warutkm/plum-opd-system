# Testing & Evaluation Guide

This guide describes how to run automated unit, integration, and regression evaluation suites for the Plum OPD Claims Adjudication system.

---

## 1. Automated Test Suite (Pytest)

The project includes 108 automated unit and integration tests located in the `backend/tests/` directory. These tests evaluate the uploader gateway, document verifier, AI extraction, normalization, validations, rule engine, RAG system, fraud engine, report generator, and confidence score calculators.

### Running Pytest:
Navigate to the `backend/` directory and execute:
```powershell
python -m pytest tests/ -v
```

### Test Coverage Areas:
- `test_adjudication.py`: Verifies end-to-end adjudication endpoints and upload flows.
- `test_api.py`: Tests API health check, list claims, and adjuster review queue endpoints.
- `test_cases_integration.py`: Runs all 10 reference test cases as API integration assertions.
- `test_confidence.py`: Verifies the 40/40/20 weighted confidence score formulas and overrides.
- `test_coverage.py`: Verifies covered and excluded medical treatments.
- `test_decision.py`: Tests composite decision and confidence score aggregation.
- `test_eligibility.py`: Verifies waiting periods, active policy checks, and age validations.
- `test_extraction_agent.py`: Verifies AI Multimodal extraction parsing and fallbacks.
- `test_financial.py`: Tests co-pays, network discounts, limits, and pre-auth exclusions.
- `test_fraud_engine.py`: Verifies Rule-Based transaction checks.
- `test_gateway_agent.py`: Tests file size and MIME-type gateway validations.
- `test_medical_necessity.py`: Verifies AI Medical Necessity evaluation and fallbacks.
- `test_normalization.py`: Validates dates, doctor registration numbers, and currency amount normalization.
- `test_partial_approval.py`: Verifies line item parsing and sub-limit split checks.
- `test_pipeline.py`: Tests direct Python rule engine and service pipeline execution.
- `test_rag.py`: Verifies Document chunker, retriever database seeding, and AI answer generator.
- `test_report.py`: Tests the structured 6-section Investigator Report.
- `test_trace_ledger.py`: Ensures chronological tracing and lifespan early-exiting.

---

## 2. Regression Evaluation (10 Test Cases)

A dedicated evaluation runner (`run_tests.py`) runs the 10 reference test cases (TC001 to TC010) against the running uvicorn server to verify end-to-end integration:

### Running Evaluation:
1. Start the API server on port `8001`:
   ```powershell
   uvicorn main:app --port 8001
   ```
2. Execute the evaluation script:
   ```powershell
   python run_tests.py
   ```

### Target Outcomes Verified:
- **TC001 (Approved)**: Simple consultation, ₹1500 limit, 10% co-pay (Payout: ₹1350).
- **TC002 (Partial)**: Dental root canal covered, whitening excluded (Payout: ₹8000).
- **TC003 (Rejected)**: Per-claim limit exceeded (Payout: ₹0).
- **TC004 (Rejected)**: Missing document attachments (Payout: ₹0).
- **TC005 (Rejected)**: Waiting period violation for pre-existing Diabetes (Payout: ₹0).
- **TC006 (Approved)**: Alternative Ayush medicine consultation (Payout: ₹4000).
- **TC007 (Rejected)**: High-value scan without pre-authorization (Payout: ₹0).
- **TC008 (Manual Review)**: Flagged for manual review due to low confidence.
- **TC009 (Rejected)**: Bariatric obesity exclusions (Payout: ₹0).
- **TC010 (Approved)**: Network Hospital 20% cashless discount (Payout: ₹3600).
