# Adjudication Evaluation Report

This report summarizes the execution outcomes of the **10 Standard Test Cases (TC001 to TC010)** run against the claims adjudication engine.

---

## 1. Executive Summary

- **Total Test Cases**: 10
- **Passed**: 10
- **Failed**: 0
- **Errors**: 0
- **Overall Pass Rate**: **100%** ✅

---

## 2. Test Case Breakdown

| Test ID | Scenario Name | Expected Decision | Actual Decision | Expected Payout | Actual Payout | Status |
|---|---|---|---|---|---|---|
| **TC001** | Simple Consultation | APPROVED | APPROVED | ₹1,350 | ₹1,350 | **PASS** |
| **TC002** | Dental Root Canal & Whitening | PARTIAL | PARTIAL | ₹8,000 | ₹8,000 | **PASS** |
| **TC003** | Limit Exceeded | REJECTED | REJECTED | ₹0 | ₹0 | **PASS** |
| **TC004** | Missing Documents | REJECTED | REJECTED | ₹0 | ₹0 | **PASS** |
| **TC005** | Waiting Period Violation | REJECTED | REJECTED | ₹0 | ₹0 | **PASS** |
| **TC006** | Alternative Ayush Medicine | APPROVED | APPROVED | ₹4,000 | ₹4,000 | **PASS** |
| **TC007** | Diagnostic scans w/o Pre-Auth | REJECTED | REJECTED | ₹0 | ₹0 | **PASS** |
| **TC008** | Fraud Flagged Manual Review | MANUAL_REVIEW | MANUAL_REVIEW | N/A | N/A | **PASS** |
| **TC009** | Obesity consultation Exclusions | REJECTED | REJECTED | ₹0 | ₹0 | **PASS** |
| **TC010** | Network Cashless Visit | APPROVED | APPROVED | ₹3,600 | ₹3,600 | **PASS** |

---

## 3. Core Engine Decisions Log

1. **TC001 (Viral Fever Consultation)**:
   - *Reasoning*: Consultation fee capped at ₹1500 limit. 10% co-pay applied. Invoice ₹1500 $\rightarrow$ Approved: ₹1350.
2. **TC002 (Root Canal & Whitening)**:
   - *Reasoning*: Teeth whitening excluded as cosmetic treatment. Root canal treatment covered. Payout: ₹8000.
3. **TC003 (Gastroenteritis Limit Exceeded)**:
   - *Reasoning*: Consultation limit and overall limits exceeded. Claims rejected with `PER_CLAIM_EXCEEDED`.
4. **TC004 (Missing Documents)**:
   - *Reasoning*: Prescription is missing (only invoice uploaded). Claims rejected with `MISSING_DOCUMENTS`.
5. **TC005 (Pre-existing Diabetes)**:
   - *Reasoning*: Treatment date is within 90 days of join date (Waiting Period). Claim rejected with `WAITING_PERIOD`.
6. **TC006 (Ayurvedic Consultation)**:
   - *Reasoning*: Alternative medicines covered under Ayush guidelines. Approved: ₹4000.
7. **TC007 (High-value MRI scan)**:
   - *Reasoning*: Diagnostic scan exceeds ₹10,000 without pre-authorization. Rejected with `PRE_AUTH_MISSING`.
8. **TC008 (Multiple Daily Claims)**:
   - *Reasoning*: Triggered Rule-Based fraud check (claims velocity limits). Overridden to `MANUAL_REVIEW`.
9. **TC009 (Obesity Consultation)**:
   - *Reasoning*: Obesity treatment is explicitly excluded in the policy terms. Rejected with `SERVICE_NOT_COVERED`.
10. **TC010 (Network Hospital Cashless)**:
    - *Reasoning*: 20% network discount applied to ₹4500 invoice before 10% co-pay (Payout: ₹3600).
