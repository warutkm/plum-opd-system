import os
import json
import logging
from datetime import date
from typing import List
from app.models.fraud import FraudSignal, FraudEngine, FraudSeverity
from app.schemas.claim_schema import AdjudicationContext
from app.database import get_db_connection, IN_MEMORY_CLAIMS

logger = logging.getLogger(__name__)

BLACKLISTED_PROVIDERS = [
    "quack",
    "quickcash clinic",
    "apex health scam",
    "fake diagnostic lab",
    "medfraud",
]

class RuleFraudEngine:
    def detect(self, ctx: AdjudicationContext) -> List[FraudSignal]:
        signals: List[FraudSignal] = []
        
        # ── Rule 1: Same member, 2 claims within 24 hours ──────────────────────
        claims_24h = ctx.previous_claims_count_24h
        member_claims = []
        
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT claim_id, treatment_date, claim_amount FROM claims WHERE member_id = (SELECT id FROM members WHERE employee_id = %s) AND claim_id != %s AND treatment_date >= %s::date - 1 AND treatment_date <= %s::date + 1",
                        (ctx.member.member_id, ctx.claim_id, ctx.treatment_date, ctx.treatment_date)
                    )
                    member_claims = cur.fetchall()
            except Exception as exc:
                logger.warning(f"Error querying DB for member claims window: {exc}")
            finally:
                conn.close()
        else:
            for cid, c in IN_MEMORY_CLAIMS.items():
                if cid == ctx.claim_id or c.get("member_id") != ctx.member.member_id:
                    continue
                t_date = c.get("treatment_date")
                if isinstance(t_date, str):
                    t_date = date.fromisoformat(t_date)
                if abs((ctx.treatment_date - t_date).days) <= 1:
                    member_claims.append(c)

        total_member_claims_24h = max(claims_24h, len(member_claims))
        if total_member_claims_24h >= 2:
            signals.append(
                FraudSignal(
                    signal_type="HIGH_FREQUENCY_CLAIMS_24H",
                    engine=FraudEngine.RULE_BASED,
                    description=f"Member submitted {total_member_claims_24h} other claims in the last 24 hours.",
                    severity=FraudSeverity.HIGH,
                    score_impact=40.0,
                    details={"count_24h": total_member_claims_24h + 1},
                )
            )
        elif total_member_claims_24h == 1:
            signals.append(
                FraudSignal(
                    signal_type="MULTIPLE_CLAIMS_24H",
                    engine=FraudEngine.RULE_BASED,
                    description="Member submitted another claim in the last 24 hours.",
                    severity=FraudSeverity.MEDIUM,
                    score_impact=20.0,
                    details={"count_24h": total_member_claims_24h + 1},
                )
            )

        # ── Rule 2: Same provider, 5 claims within 7 days ──────────────────────
        provider_name = (ctx.extracted_data.provider_name or ctx.hospital_name or "").lower().strip()
        provider_claims = []
        if provider_name:
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT c.claim_id FROM claims c JOIN extracted_data ed ON ed.claim_id = c.id WHERE LOWER(TRIM(ed.provider_name)) = %s AND c.claim_id != %s AND c.treatment_date >= %s::date - 7 AND c.treatment_date <= %s::date + 7",
                            (provider_name, ctx.claim_id, ctx.treatment_date, ctx.treatment_date)
                        )
                        provider_claims = cur.fetchall()
                except Exception as exc:
                    logger.warning(f"Error querying DB for provider claims window: {exc}")
                finally:
                    conn.close()
            else:
                for cid, c in IN_MEMORY_CLAIMS.items():
                    if cid == ctx.claim_id:
                        continue
                    c_prov = (c.get("hospital_name") or c.get("extracted_data", {}).get("provider_name") or "").lower().strip()
                    if c_prov == provider_name:
                        t_date = c.get("treatment_date")
                        if isinstance(t_date, str):
                            t_date = date.fromisoformat(t_date)
                        if abs((ctx.treatment_date - t_date).days) <= 7:
                            provider_claims.append(c)

            total_provider_claims = len(provider_claims) + 1
            if total_provider_claims >= 5:
                signals.append(
                    FraudSignal(
                        signal_type="HIGH_FREQUENCY_PROVIDER_7D",
                        engine=FraudEngine.RULE_BASED,
                        description=f"Provider '{provider_name}' has {total_provider_claims} claims submitted within 7 days.",
                        severity=FraudSeverity.HIGH,
                        score_impact=30.0,
                        details={"provider_name": provider_name, "count_7d": total_provider_claims},
                    )
                )

        # ── Rule 3: Diagnosis-age mismatch (LLM assisted) ─────────────────────
        diagnosis = ctx.extracted_data.diagnosis
        age = ctx.member.age
        if not age and ctx.member.date_of_birth:
            age = ctx.treatment_date.year - ctx.member.date_of_birth.year
        if not age and ctx.extracted_data.age:
            try:
                age = int(ctx.extracted_data.age)
            except ValueError:
                pass

        if os.getenv("GEMINI_API_KEY") and diagnosis and age:
            try:
                import google.generativeai as genai
                prompt = f"""
                You are a clinical fraud auditor. Your job is to detect physiological anomalies or mismatches between a patient's age and their medical diagnosis.
                
                Patient Age: {age}
                Diagnosis: {diagnosis}
                
                Analyze if this is a physiological anomaly or clear clinical mismatch (e.g. pregnancy or senile dementia in an infant/child, pediatric-exclusive genetic diseases in elderly).
                
                Return ONLY a JSON response in the following format:
                {{
                    "mismatch_detected": boolean,
                    "reasoning": "string explanation of why there is or is not a mismatch"
                }}
                """
                model = genai.GenerativeModel("gemini-2.5-flash-lite")
                generation_config = {"response_mime_type": "application/json"}
                response = model.generate_content(prompt, generation_config=generation_config)
                result = json.loads(response.text)
                
                if result.get("mismatch_detected"):
                    signals.append(
                        FraudSignal(
                            signal_type="DIAGNOSIS_AGE_MISMATCH",
                            engine=FraudEngine.RULE_BASED,
                            description=f"LLM detected diagnosis-age anomaly: {result.get('reasoning')}",
                            severity=FraudSeverity.HIGH,
                            score_impact=35.0,
                            details={"age": age, "diagnosis": diagnosis, "reasoning": result.get("reasoning")},
                        )
                    )
            except Exception as exc:
                logger.error(f"Failed to check diagnosis-age mismatch: {exc}")

        # ── Rule 4: Duplicate bill number (Database lookup) ─────────────────
        bill_number = ctx.extracted_data.bill_number
        if bill_number:
            bill_number_clean = bill_number.strip().upper()
            duplicate_bill = False
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT c.claim_id FROM claims c JOIN extracted_data ed ON ed.claim_id = c.id WHERE UPPER(TRIM(ed.normalized_data->>'bill_number')) = %s AND c.claim_id != %s",
                            (bill_number_clean, ctx.claim_id)
                        )
                        row = cur.fetchone()
                        if row:
                            duplicate_bill = True
                except Exception as exc:
                    logger.warning(f"Error querying DB for duplicate bill: {exc}")
                finally:
                    conn.close()
            else:
                for cid, c in IN_MEMORY_CLAIMS.items():
                    if cid == ctx.claim_id:
                        continue
                    ext = c.get("extracted_data", {})
                    # Get bill number from extracted_data Pydantic model or dict
                    c_bill = ""
                    if isinstance(ext, dict):
                        c_bill = (ext.get("bill_number") or ext.get("normalized_data", {}).get("bill_number") or "")
                    else:
                        c_bill = (getattr(ext, "bill_number", None) or ext.normalized_data.get("bill_number") or "")
                    
                    if str(c_bill).strip().upper() == bill_number_clean:
                        duplicate_bill = True
                        break

            if duplicate_bill:
                signals.append(
                    FraudSignal(
                        signal_type="DUPLICATE_BILL_NUMBER",
                        engine=FraudEngine.RULE_BASED,
                        description=f"Bill number '{bill_number}' has already been submitted in another claim.",
                        severity=FraudSeverity.CRITICAL,
                        score_impact=60.0,
                        details={"bill_number": bill_number},
                    )
                )

        # ── Provider Blacklist Check ──────────────────────────────────────────
        provider = (ctx.extracted_data.provider_name or "").lower().strip()
        doctor = (ctx.extracted_data.doctor_name or "").lower().strip()

        for blacklisted in BLACKLISTED_PROVIDERS:
            if blacklisted in provider or blacklisted in doctor:
                signals.append(
                    FraudSignal(
                        signal_type="BLACKLISTED_PROVIDER",
                        engine=FraudEngine.RULE_BASED,
                        description="Claim submitted from blacklisted or suspicious provider",
                        severity=FraudSeverity.CRITICAL,
                        score_impact=80.0,
                        details={"matched_keyword": blacklisted},
                    )
                )
                break

        # ── High Value claim check ────────────────────────────────────────────
        if ctx.claim_amount > 25000:
            signals.append(
                FraudSignal(
                    signal_type="HIGH_VALUE_CLAIM",
                    engine=FraudEngine.RULE_BASED,
                    description="OPD Claim amount is unusually high (> ₹25,000), referring for manual review.",
                    severity=FraudSeverity.MEDIUM,
                    score_impact=15.0,
                    details={"claim_amount": ctx.claim_amount},
                )
            )

        return signals