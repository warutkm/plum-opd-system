# Fraud Detection System Design

The Plum OPD Claim Adjudication System features a layered fraud detection system combining traditional rule-based logic with high-dimensional vector similarity.

---

## 1. Engine 1 — Rule-Based Fraud Detection

Traditional fraud rules check for transactional patterns and metadata inconsistencies using direct lookup logic:

- **Rule 1 (Member Claim Velocity)**: Checks if the same member submits **2 or more claims within 24 hours**. Flags high-velocity claiming patterns.
- **Rule 2 (Provider Claim Velocity)**: Checks if the same healthcare provider (clinic/hospital) appears in **5 or more claims within 7 days** from the same company account.
- **Rule 3 (Diagnosis-Age Inconsistency)**: An LLM-assisted check flags age-inconsistent medical diagnoses (e.g., pediatric conditions in adult members, geriatric conditions like cataracts in children).
- **Rule 4 (Duplicate Invoice Number)**: Direct database lookup flags duplicate invoice/bill numbers from the same provider.

---

## 2. Engine 2 — High-Dimensional Vector Fraud Detection

Vector-based fraud detection identifies semantically similar claims that bypass traditional exact-match checks (e.g., a member submitting different invoices from different clinics but describing identical procedures, fees, and diagnoses).

### Workflow:
1. **Claim Profile Builder**: Assembles a text profile of the claim metadata:
   `Member: EMP008 | Diagnosis: Migraine | Provider: ABC Clinic | Treatment: Consultation | Amount: 4800.0`
2. **Embedding Generation**: Generates a 768-dimensional text embedding vector using the Google Gemini model.
3. **Similarity Search**: Queries historical claims in the vector database using cosine similarity:
   - **`NEAR_EXACT_DUPLICATE_PATTERN`**: similarity $\ge 0.99$. Signals direct duplicate submissions.
   - **`POTENTIAL_DUPLICATE_PATTERN`**: similarity $\ge 0.96$. Signals highly similar clinic-hopping behavior.

---

## 3. Aggregated Fraud Score

The **Fraud Score Aggregator** aggregates signals from both engines to calculate a composite `0–100` score:

- Traditional rule violations add fixed increments (e.g., `+30` for daily limit violations).
- Semantic vector similarity signals add weighted values based on similarity scores.
- **Critical Safety Override Rule**: Vector fraud checks are advisory and **never directly reject claims**. If the aggregate fraud score is $\ge 70$, the claim is overridden to `MANUAL_REVIEW`, routing it to an adjuster instead of auto-rejecting.
- **Confidence Engine Cap**: If the fraud score is $\ge 40$, the confidence engine caps the claim confidence at `0.65`, forcing a `MANUAL_REVIEW` route.
