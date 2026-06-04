# Supabase/PostgreSQL connection
import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

_logger = logging.getLogger(__name__)

# Module-level flag: once a connection attempt fails we stop retrying for
# the lifetime of the process.  This prevents repeated slow DNS look-ups
# for the unreachable "db" hostname when running outside Docker.
_db_available: bool | None = None  # None = not yet tested

def get_db_connection():
    global _db_available
    if _db_available is False:
        return None
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        _db_available = False
        return None
    try:
        conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor, connect_timeout=1)
        _db_available = True
        return conn
    except Exception as exc:
        _logger.info(f"Database unavailable, disabling persistence for this session: {exc}")
        _db_available = False
        return None


def reset_db_availability():
    """Allow re-probing after a configuration change (useful for tests)."""
    global _db_available
    _db_available = None

IN_MEMORY_CLAIMS = {}

def save_claim_to_db(
    ctx,
    rule_result,
    fraud_result,
    traces,
    report,
    final_decision: str,
    final_confidence: float,
    notes: str,
    embedding = None
) -> None:
    """
    Persist all claim adjudication details, including policies, members,
    claims, extracted data, audit traces, fraud signals, and reports to PostgreSQL.
    """
    import json
    from datetime import date
    
    conn = get_db_connection()
    if not conn:
        return
        
    try:
        with conn:
            with conn.cursor() as cur:
                # 1. Policies Table
                policy_code = ctx.member.policy_id or "POL_OPD_ADVANTAGE"
                policy_name = "Plum OPD Advantage"
                cur.execute("SELECT id FROM policies WHERE policy_code = %s", (policy_code,))
                row = cur.fetchone()
                if row:
                    policy_uuid = row["id"]
                else:
                    cur.execute(
                        """
                        INSERT INTO policies (policy_code, policy_name, company_name, effective_date, coverage_details, waiting_periods, exclusions, network_hospitals)
                        VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb)
                        RETURNING id
                        """,
                        (
                            policy_code,
                            policy_name,
                            "Plum",
                            date(2024, 1, 1),
                            "{}",
                            "{}",
                            "[]",
                            "[]"
                        )
                    )
                    policy_uuid = cur.fetchone()["id"]

                # 2. Members Table
                member_id = ctx.member.member_id
                cur.execute("SELECT id FROM members WHERE employee_id = %s", (member_id,))
                row = cur.fetchone()
                if row:
                    member_uuid = row["id"]
                else:
                    cur.execute(
                        """
                        INSERT INTO members (employee_id, name, join_date, policy_id, relationship)
                        VALUES (%s, %s, %s, %s, %s::member_relationship)
                        RETURNING id
                        """,
                        (
                            member_id,
                            ctx.member.name,
                            ctx.member.join_date,
                            policy_uuid,
                            ctx.member.relationship.upper() if ctx.member.relationship else "SELF"
                        )
                    )
                    member_uuid = cur.fetchone()["id"]

                # 3. Claims Table
                status_val = "DECIDED" if final_decision != "MANUAL_REVIEW" else "MANUAL_REVIEW"
                decision_val = final_decision
                
                cur.execute("SELECT id FROM claims WHERE claim_id = %s", (ctx.claim_id,))
                row = cur.fetchone()
                
                rejection_reasons_json = json.dumps(list(rule_result.rejection_reasons))
                decision_metadata_json = json.dumps({
                    "notes": notes,
                    "rejected_items": rule_result.rejected_items,
                    "is_cashless_approved": rule_result.is_cashless_approved,
                })
                
                if row:
                    claim_uuid = row["id"]
                    cur.execute(
                        """
                        UPDATE claims
                        SET approved_amount = %s, status = %s::claim_status, decision = %s::claim_decision,
                            confidence_score = %s, fraud_score = %s, rejection_reasons = %s::jsonb,
                            decision_metadata = %s::jsonb, updated_at = NOW()
                        WHERE id = %s
                        """,
                        (
                            rule_result.approved_amount if final_decision != "REJECTED" else 0.0,
                            status_val,
                            decision_val,
                            final_confidence,
                            fraud_result.fraud_score,
                            rejection_reasons_json,
                            decision_metadata_json,
                            claim_uuid
                        )
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO claims (claim_id, member_id, claim_amount, approved_amount, status, decision, confidence_score, fraud_score, rejection_reasons, decision_metadata, hospital_name, treatment_date, is_cashless, is_network_hospital)
                        VALUES (%s, %s, %s, %s, %s::claim_status, %s::claim_decision, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            ctx.claim_id,
                            member_uuid,
                            ctx.claim_amount,
                            rule_result.approved_amount if final_decision != "REJECTED" else 0.0,
                            status_val,
                            decision_val,
                            final_confidence,
                            fraud_result.fraud_score,
                            rejection_reasons_json,
                            decision_metadata_json,
                            ctx.hospital_name,
                            ctx.treatment_date,
                            ctx.is_cashless,
                            ctx.is_network_hospital
                        )
                    )
                    claim_uuid = cur.fetchone()["id"]

                # 4. Extracted Data Table
                extracted_data = ctx.extracted_data
                if extracted_data:
                    medicines_json = json.dumps(extracted_data.medicines)
                    procedures_json = json.dumps(extracted_data.procedures)
                    tests_json = json.dumps(extracted_data.tests)
                    raw_ext_json = json.dumps(extracted_data.raw_extraction)
                    norm_data_json = json.dumps(extracted_data.normalized_data)
                    
                    cur.execute(
                        """
                        INSERT INTO extracted_data (claim_id, patient_name, age, doctor_name, doctor_registration, diagnosis, medicines, procedures, tests, provider_name, bill_amount, treatment_date, extraction_confidence, raw_extraction, normalized_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                        ON CONFLICT (claim_id) DO UPDATE SET
                            patient_name = EXCLUDED.patient_name,
                            age = EXCLUDED.age,
                            doctor_name = EXCLUDED.doctor_name,
                            doctor_registration = EXCLUDED.doctor_registration,
                            diagnosis = EXCLUDED.diagnosis,
                            medicines = EXCLUDED.medicines,
                            procedures = EXCLUDED.procedures,
                            tests = EXCLUDED.tests,
                            provider_name = EXCLUDED.provider_name,
                            bill_amount = EXCLUDED.bill_amount,
                            treatment_date = EXCLUDED.treatment_date,
                            extraction_confidence = EXCLUDED.extraction_confidence,
                            raw_extraction = EXCLUDED.raw_extraction,
                            normalized_data = EXCLUDED.normalized_data
                        """,
                        (
                            claim_uuid,
                            extracted_data.patient_name,
                            str(extracted_data.age) if extracted_data.age is not None else None,
                            extracted_data.doctor_name,
                            extracted_data.doctor_registration,
                            extracted_data.diagnosis,
                            medicines_json,
                            procedures_json,
                            tests_json,
                            extracted_data.provider_name,
                            extracted_data.bill_amount,
                            extracted_data.treatment_date,
                            extracted_data.extraction_confidence,
                            raw_ext_json,
                            norm_data_json
                        )
                    )

                # 5. Claim Embeddings Table
                if embedding:
                    cur.execute(
                        """
                        INSERT INTO claim_embeddings (claim_id, embedding, metadata)
                        VALUES (%s, %s, %s::jsonb)
                        ON CONFLICT (claim_id) DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata
                        """,
                        (
                            claim_uuid,
                            embedding,
                            json.dumps({"diagnosis": extracted_data.diagnosis, "provider": extracted_data.provider_name})
                        )
                    )

                # 6. Fraud Signals Table
                cur.execute("DELETE FROM fraud_signals WHERE claim_id = %s", (claim_uuid,))
                for sig in fraud_result.signals:
                    cur.execute(
                        """
                        INSERT INTO fraud_signals (claim_id, signal_type, engine, description, severity, score_impact, details)
                        VALUES (%s, %s, %s::fraud_engine, %s, %s::fraud_severity, %s, %s::jsonb)
                        """,
                        (
                            claim_uuid,
                            sig.signal_type,
                            sig.engine.value,
                            sig.description,
                            sig.severity.value,
                            sig.score_impact,
                            json.dumps(sig.details)
                        )
                    )

                # 7. Investigator Reports Table
                if report:
                    report_dict = report.model_dump() if hasattr(report, 'model_dump') else report
                    cur.execute(
                        """
                        INSERT INTO investigator_reports (claim_id, claim_summary, coverage_analysis, limit_analysis, fraud_analysis, decision_rationale, what_if_analysis, policy_references, full_report_text)
                        VALUES (%s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)
                        ON CONFLICT (claim_id) DO UPDATE SET
                            claim_summary = EXCLUDED.claim_summary,
                            coverage_analysis = EXCLUDED.coverage_analysis,
                            limit_analysis = EXCLUDED.limit_analysis,
                            fraud_analysis = EXCLUDED.fraud_analysis,
                            decision_rationale = EXCLUDED.decision_rationale,
                            what_if_analysis = EXCLUDED.what_if_analysis,
                            policy_references = EXCLUDED.policy_references,
                            full_report_text = EXCLUDED.full_report_text
                        """,
                        (
                            claim_uuid,
                            json.dumps(report_dict.get("claim_summary", {})),
                            json.dumps(report_dict.get("coverage_analysis", {})),
                            json.dumps(report_dict.get("limit_analysis", {})),
                            json.dumps(report_dict.get("fraud_analysis", {})),
                            json.dumps(report_dict.get("decision_rationale", {})),
                            json.dumps(report_dict.get("what_if_analysis", {})),
                            json.dumps(report_dict.get("policy_references", [])),
                            report_dict.get("full_report_text", "")
                        )
                    )

                # 8. Audit Traces Table
                cur.execute("DELETE FROM audit_traces WHERE claim_id = %s", (claim_uuid,))
                for order, trace in enumerate(traces):
                    cur.execute(
                        """
                        INSERT INTO audit_traces (trace_id, claim_id, step, status, details, step_order, duration_ms)
                        VALUES (%s, %s, %s, %s::trace_status, %s::jsonb, %s, %s)
                        """,
                        (
                            f"TRC_{ctx.claim_id}_{order}",
                            claim_uuid,
                            trace.step,
                            trace.status,
                            json.dumps(trace.details),
                            order,
                            trace.duration_ms
                        )
                    )
    except Exception as exc:
        # Gracefully handle database constraint/connection errors
        import logging
        logging.getLogger(__name__).warning(f"Failed to persist claim to PostgreSQL database: {exc}")
    finally:
        conn.close()