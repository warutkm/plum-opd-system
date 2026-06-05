# Policy Rules & Adjudication Assumptions

This document lists the rules, thresholds, and business logic assumptions implemented in the Plum OPD Claims Adjudication Engine.

---

## 1. Eligibility & Waiting Periods
- **Policy Activation**: A claim is rejected with `POLICY_INACTIVE` if the treatment date is outside the policy start/end dates.
- **Disease-Specific Waiting Periods**:
  - **Diabetes & Hypertension**: Requires a **90-day waiting period** from the member join date to the treatment date.
  - **Joint Replacement & Cataract**: Requires a **730-day (2-year) waiting period** from the member join date.
  - Other acute conditions (e.g., viral fever, gastroenteritis) have a **0-day waiting period**.

---

## 2. Documentation Rules
- **Required Documents**: A claim must contain both a **prescription** (justifying treatment) and an **invoice/bill** (verifying payment).
- **Date Matching**: The treatment date on the invoice must match the date submitted in the claim metadata within a **3-day grace period**.
- **Doctor Verification**: A doctor's registration number (e.g., `KA/45678/2015`) must be present. If missing or invalid, the claim is flagged with `INVALID_PRESCRIPTION`.
- **Member Name Matching**: The patient name extracted from the invoice/prescription must match the member's profile name. We allow minor variations (such as initials or ordering) but enforce a **85% similarity match threshold**.

---

## 3. Financial Limits & Deductibles
- **Consultation Limit**: Consultation fees are capped at **₹1,500 per claim**.
- **Diagnostic/Laboratory Tests**: Tests are capped at **₹5,000 per claim**.
- **Co-Pay**: A standard **10% co-pay** is deducted from the approved amount for all claims.
- **Network Cashless Discount**: If the claim is submitted as cashless at a **Network Hospital** (e.g., *Apollo Hospitals*), a **20% network discount** is deducted from the invoice amount instead of the standard co-pay.
- **Pre-Authorization**: High-value diagnostic tests or procedures exceeding **₹10,000** require pre-authorization. If not pre-authorized, the claim is rejected with `PRE_AUTH_MISSING`.

---

## 4. Exclusion List
OPD coverage excludes the following services:
- **Cosmetic & Aesthetic Procedures**: Acne scar removals, anti-aging therapies.
- **Teeth Whitening & Aesthetics**: Standard dental scaling is covered, but cosmetic teeth whitening is excluded with `COSMETIC_EXCLUSION`.
- **Weight Loss/Obesity**: Bariatric consultations, nutrition plans, or dietary supplements are excluded with `SERVICE_NOT_COVERED`.
- **Experimental Treatments**: Alternative therapies not recognized by national medical boards.
