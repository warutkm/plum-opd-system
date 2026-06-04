# Testing & Evaluation Guide

This guide describes how to run automated unit, integration, and regression evaluation suites for the Plum OPD Claims Adjudication system.

---

## 1. Automated Test Suite (Pytest)

The project includes 84 automated unit and integration tests located in the `backend/tests/` directory. These tests evaluate the rule engine, RAG system, fraud engine, and confidence score calculators.

### Running Pytest:
Navigate to the `backend/` directory and execute:
```powershell
python -m pytest tests/
```

### Test Coverage Areas:
- `test_eligibility.py`: Verifies waiting periods, active policy checks, and age validations.
- `test_coverage.py`: Verifies covered and excluded medical treatments.
- `test_financial.py`: Tests co-pays, network discounts, limits, and pre-auth exclusions.
- `test_fraud_engine.py`: Verifies Rule-Based transaction checks.
- `test_vector_fraud.py`: Verifies claim profile generation and vector search mock bounds.
- `test_confidence.py`: Verifies the 40/40/20 weighted confidence score formulas.
- `test_trace_ledger.py`: Ensures chronological tracing and lifespan early-exiting.
- `test_report.py`: Tests the structured 6-section Investigator Report.

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
