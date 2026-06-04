import time
from datetime import date
from typing import Dict, List, Optional, Tuple, Any

from app.models.claim import ClaimDecision
from app.models.policy import PolicyTerms
from app.schemas.claim_schema import AdjudicationContext, ExtractedData
from app.schemas.api_schema import ClaimDecisionOutput
from app.models.member import Member
from app.models.audit import AuditTraceEntry

from app.agents.gateway_agent import GatewayAgent
from app.agents.document_verification_agent import DocumentVerificationAgent
from app.agents.extraction_agent import MultimodalExtractionAgent
from app.agents.normalization_agent import NormalizationAgent
from app.agents.validation_agent import ValidationAgent
from app.agents.medical_necessity_agent import MedicalNecessityAgent
from app.engine.rule_engine import DeterministicRuleEngine
from app.fraud.fraud_aggregator import FraudAggregator

class ClaimService:
    def __init__(self, policy_terms: PolicyTerms):
        self.policy = policy_terms
        self.gateway = GatewayAgent()
        self.doc_verifier = DocumentVerificationAgent()
        self.extraction = MultimodalExtractionAgent()
        self.normalization = NormalizationAgent(network_hospitals=policy_terms.network_hospitals)
        self.validation = ValidationAgent()
        self.necessity = MedicalNecessityAgent()
        self.rule_engine = DeterministicRuleEngine(policy_terms)
        self.fraud_engine = FraudAggregator()

    def process_claim(
        self,
        member: Member,
        claim_amount: float,
        treatment_date: date,
        hospital_name: Optional[str] = None,
        is_cashless: bool = False,
        file_contents: Optional[List[Tuple[bytes, str]]] = None,
        pre_extracted_data: Optional[ExtractedData] = None,
        pre_bill_items: Optional[Dict[str, float]] = None,
        previous_claims_same_day: int = 0,
        ytd_approved_total: float = 0.0,
        has_pre_auth: bool = False,
        claim_id_override: Optional[str] = None,
    ) -> ClaimDecisionOutput:
        traces: List[AuditTraceEntry] = []
        pipeline_start = time.time()

        # Phase 1: Gateway
        gw_status, claim_id, gw_details, gw_trace = self.gateway.process(file_contents, claim_id_override)
        traces.append(gw_trace)
        if gw_status == "FAIL":
            return ClaimDecisionOutput(
                claim_id=claim_id,
                decision=ClaimDecision.REJECTED.value,
                rejection_reasons=["GATEWAY_FILE_INVALID"],
                notes=gw_details.get("error", "Gateway validation failed"),
                trace_summary=traces,
            )

        # Phase 1: Document Verification
        doc_status, doc_details, doc_trace = self.doc_verifier.process(file_contents, pre_extracted_data, pre_bill_items)
        traces.append(doc_trace)

        # Phase 2: Extraction
        extracted_data = pre_extracted_data or ExtractedData()
        # Pre-extracted data bypasses AI extraction — treat as reliable
        if pre_extracted_data and extracted_data.extraction_confidence == 0.0:
            extracted_data.extraction_confidence = 0.95
        start = time.time()
        if file_contents and doc_status == "PASS":
            extracted_data = self.extraction.process(file_contents)
            extraction_status = "PASS" if extracted_data.extraction_confidence > 0.0 else "FAIL"
        else:
            extraction_status = "SKIP"
        
        traces.append(AuditTraceEntry(
            step="ai_extraction",
            status=extraction_status,
            details={"confidence": extracted_data.extraction_confidence, "diagnosis": extracted_data.diagnosis, "provider": extracted_data.provider_name},
            duration_ms=int((time.time() - start) * 1000)
        ))

        # Phase 2B: Normalization
        norm_status, norm_details, norm_trace = self.normalization.process(extracted_data, pre_bill_items)
        traces.append(norm_trace)

        # Phase 2B: Validation
        val_status, val_details, val_trace = self.validation.process(extracted_data, member, treatment_date)
        traces.append(val_trace)

        # Phase 4: Medical Necessity
        start = time.time()
        if extraction_status == "PASS" or pre_extracted_data:
            necessity_result = self.necessity.process(extracted_data)
            necessity_status = "PASS" if necessity_result.medically_necessary else "WARNING"
        else:
            necessity_status = "SKIP"
            necessity_result = None

        traces.append(AuditTraceEntry(
            step="medical_necessity_check",
            status=necessity_status,
            details={"medically_necessary": necessity_result.medically_necessary if necessity_result else None, "reasoning": necessity_result.reasoning if necessity_result else None},
            duration_ms=int((time.time() - start) * 1000)
        ))

        # Phase 5: Deterministic Rules
        from app.engine.utils import is_network_hospital
        is_network = False
        if hospital_name:
            is_network = is_network_hospital(hospital_name, self.policy)
        elif extracted_data.provider_name:
            is_network = is_network_hospital(extracted_data.provider_name, self.policy)

        ctx = AdjudicationContext(
            claim_id=claim_id,
            member=member,
            claim_amount=claim_amount,
            treatment_date=treatment_date,
            documents_submitted=["prescription", "bill"] if doc_status == "PASS" else ["bill"],
            extracted_data=extracted_data,
            bill_items=extracted_data.bill_items,
            hospital_name=hospital_name or extracted_data.provider_name,
            is_cashless=is_cashless,
            is_network_hospital=is_network,
            has_pre_authorization=has_pre_auth,
            ytd_approved_total=ytd_approved_total,
            previous_claims_count_24h=previous_claims_same_day,
        )

        start = time.time()
        rule_result = self.rule_engine.adjudicate(ctx)
        traces.append(AuditTraceEntry(
            step="deterministic_rules_check",
            status="PASS" if rule_result.decision != ClaimDecision.REJECTED else "FAIL",
            details={"engine_decision": rule_result.decision.value, "approved_amount": rule_result.approved_amount, "rejection_reasons": rule_result.rejection_reasons},
            duration_ms=int((time.time() - start) * 1000)
        ))

        # Phase 6: Fraud Detection
        start = time.time()
        fraud_result = self.fraud_engine.detect(ctx)
        has_high_fraud = any(sig.severity.value in ["HIGH", "CRITICAL"] for sig in fraud_result.signals)

        fraud_duration = int((time.time() - start) * 1000)

        # Separate trace entries for rule-based and vector fraud checks
        # as specified in the trace ledger (Point 9 of the architecture doc)
        rule_signals = [s for s in fraud_result.signals if s.engine.value == "RULE_BASED"]
        vector_signals = [s for s in fraud_result.signals if s.engine.value == "VECTOR_SIMILARITY"]

        traces.append(AuditTraceEntry(
            step="fraud_detection_check",
            status="PASS" if not rule_signals else "WARNING",
            details={
                "fraud_score": fraud_result.fraud_score,
                "rule_based_signals": len(rule_signals),
                "signal_types": [s.signal_type for s in rule_signals],
            },
            duration_ms=fraud_duration,
        ))

        traces.append(AuditTraceEntry(
            step="vector_fraud_check",
            status="PASS" if not vector_signals else "WARNING",
            details={
                "vector_signals": len(vector_signals),
                "signal_types": [s.signal_type for s in vector_signals],
                "requires_manual_review": fraud_result.requires_manual_review,
            },
            duration_ms=fraud_duration,
        ))

        # Decision Aggregator + Confidence Engine (Point 8)
        from app.services.decision_service import DecisionAggregator
        decision_aggregator = DecisionAggregator()
        final_decision, final_confidence, next_steps, notes, confidence_breakdown = decision_aggregator.aggregate(
            extracted_data, rule_result, fraud_result, doc_status, has_high_fraud
        )

        # Confidence Engine trace entry (Point 8)
        traces.append(AuditTraceEntry(
            step="confidence_engine",
            status="PASS" if final_confidence >= 0.70 else "WARNING",
            details={
                "extraction_confidence": confidence_breakdown.extraction_confidence,
                "rule_confidence": confidence_breakdown.rule_confidence,
                "fraud_doc_quality": confidence_breakdown.fraud_doc_quality,
                "final_confidence": confidence_breakdown.final_confidence,
                "formula": "40% extraction + 40% rule + 20% fraud/doc quality",
            },
            duration_ms=int((time.time() - start) * 1000),
        ))
        
        traces.append(AuditTraceEntry(
            step="decision_aggregator",
            status="PASS" if final_decision in ["APPROVED", "PARTIAL"] else "WARNING",
            details={"final_decision": final_decision, "confidence_score": final_confidence, "fraud_score": fraud_result.fraud_score},
            duration_ms=int((time.time() - start) * 1000)
        ))

        network_discount = 0.0
        deductions = {}
        if rule_result.financial and rule_result.financial.breakdown:
            bd = rule_result.financial.breakdown
            if bd.copay_amount > 0:
                deductions["copay"] = bd.copay_amount
            if bd.network_discount_amount > 0:
                network_discount = bd.network_discount_amount
                deductions["network_discount"] = network_discount
        from app.services.report_service import ReportService
        report_service = ReportService()
        report = report_service.generate_investigator_report(ctx, rule_result, fraud_result)

        # Retrieve embedding if generated
        embedding = None
        if hasattr(self.fraud_engine, "vector_engine") and hasattr(self.fraud_engine.vector_engine, "_local_embeddings_cache"):
            for cache in self.fraud_engine.vector_engine._local_embeddings_cache:
                if cache.get("claim_id") == claim_id:
                    embedding = cache.get("embedding")
                    break

        # Persist claim state to PostgreSQL database
        from app.database import save_claim_to_db
        save_claim_to_db(
            ctx=ctx,
            rule_result=rule_result,
            fraud_result=fraud_result,
            traces=traces,
            report=report,
            final_decision=final_decision,
            final_confidence=final_confidence,
            notes=notes,
            embedding=embedding,
        )

        return ClaimDecisionOutput(
            claim_id=claim_id,
            decision=final_decision,
            approved_amount=rule_result.approved_amount if final_decision != "REJECTED" else 0.0,
            rejection_reasons=list(rule_result.rejection_reasons),
            rejected_items=rule_result.rejected_items,
            confidence_score=final_confidence,
            fraud_score=fraud_result.fraud_score,
            notes=notes,
            next_steps=next_steps,
            is_cashless_approved=rule_result.is_cashless_approved,
            network_discount=network_discount,
            deductions=deductions,
            trace_summary=traces,
            investigator_report=report,
            confidence_breakdown=confidence_breakdown,
        )