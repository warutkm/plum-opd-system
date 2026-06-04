"""
Tests for the Vector Fraud Detection Engine (Point 7, Engine 2).

Verifies:
    1. No false positives on clean claims
    2. POTENTIAL_DUPLICATE_PATTERN triggered at similarity > 0.96
    3. NEAR_EXACT_DUPLICATE_PATTERN triggered at similarity > 0.99
    4. Fraud Profile Builder produces correct structured profiles
    5. Safety rule: vector signals never exceed HIGH severity
    6. Aggregator properly combines rule-based + vector signals
    7. Local cache fallback works correctly
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from app.models.member import Member
from app.models.fraud import FraudEngine, FraudSeverity
from app.schemas.claim_schema import AdjudicationContext, ExtractedData
from app.fraud.vector_fraud_engine import VectorFraudEngine
from app.fraud.fraud_aggregator import FraudAggregator
from app.fraud.fraud_profile import FraudProfileBuilder


# ── Fraud Profile Builder Tests ───────────────────────────────────────────

class TestFraudProfileBuilder:
    """Tests for the Fraud Profile Builder component."""

    def test_basic_profile(self):
        member = Member(
            member_id="EMP001", name="John Doe",
            join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE",
        )
        ctx = AdjudicationContext(
            claim_id="CLM_001",
            member=member,
            claim_amount=4800.0,
            treatment_date=date(2024, 6, 1),
            extracted_data=ExtractedData(
                diagnosis="Migraine",
                provider_name="ABC Clinic",
            ),
        )
        profile = FraudProfileBuilder.build_profile_text(ctx)
        assert "Diagnosis: Migraine" in profile
        assert "Provider: ABC Clinic" in profile
        assert "Amount: 4800.0" in profile
        assert "Treatment: Consultation" in profile  # default when no procedures
        assert "Member: EMP001" in profile

    def test_profile_with_procedures(self):
        member = Member(
            member_id="EMP001", name="John Doe",
            join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE",
        )
        ctx = AdjudicationContext(
            claim_id="CLM_001",
            member=member,
            claim_amount=8000.0,
            treatment_date=date(2024, 6, 1),
            extracted_data=ExtractedData(
                diagnosis="Dental Caries",
                provider_name="Dental Care",
                procedures=["Root Canal", "Filling"],
            ),
        )
        profile = FraudProfileBuilder.build_profile_text(ctx)
        assert "Treatment: Root Canal, Filling" in profile

    def test_profile_with_tests(self):
        member = Member(
            member_id="EMP001", name="John Doe",
            join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE",
        )
        ctx = AdjudicationContext(
            claim_id="CLM_001",
            member=member,
            claim_amount=3000.0,
            treatment_date=date(2024, 6, 1),
            extracted_data=ExtractedData(
                diagnosis="Diabetes",
                provider_name="HealthLab",
                tests=["HbA1c", "Fasting Blood Sugar"],
            ),
        )
        profile = FraudProfileBuilder.build_profile_text(ctx)
        assert "HbA1c" in profile
        assert "Fasting Blood Sugar" in profile

    def test_profile_with_medicines_only(self):
        member = Member(
            member_id="EMP001", name="John Doe",
            join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE",
        )
        ctx = AdjudicationContext(
            claim_id="CLM_001",
            member=member,
            claim_amount=500.0,
            treatment_date=date(2024, 6, 1),
            extracted_data=ExtractedData(
                diagnosis="Cold",
                provider_name="MedPlus",
                medicines=["Paracetamol", "Cetirizine"],
            ),
        )
        profile = FraudProfileBuilder.build_profile_text(ctx)
        assert "Treatment: Pharmacy" in profile

    def test_profile_metadata(self):
        member = Member(
            member_id="EMP001", name="John Doe",
            join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE",
        )
        ctx = AdjudicationContext(
            claim_id="CLM_001",
            member=member,
            claim_amount=4800.0,
            treatment_date=date(2024, 6, 1),
            extracted_data=ExtractedData(
                diagnosis="Migraine",
                provider_name="ABC Clinic",
            ),
        )
        metadata = FraudProfileBuilder.build_profile_metadata(ctx)
        assert metadata["claim_id"] == "CLM_001"
        assert metadata["member_id"] == "EMP001"
        assert metadata["diagnosis"] == "Migraine"
        assert metadata["provider"] == "ABC Clinic"
        assert metadata["amount"] == 4800.0

    def test_hospital_name_fallback(self):
        """When extracted_data has no provider_name, fall back to hospital_name."""
        member = Member(
            member_id="EMP001", name="John Doe",
            join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE",
        )
        ctx = AdjudicationContext(
            claim_id="CLM_001",
            member=member,
            claim_amount=1000.0,
            treatment_date=date(2024, 6, 1),
            hospital_name="City Hospital",
            extracted_data=ExtractedData(diagnosis="Fever"),
        )
        profile = FraudProfileBuilder.build_profile_text(ctx)
        assert "Provider: City Hospital" in profile


# ── Vector Fraud Engine Tests ─────────────────────────────────────────────

class TestVectorFraudEngine:
    """Tests for the Vector Fraud Engine."""

    @patch("google.generativeai.embed_content")
    def test_no_match_on_clean_claim(self, mock_embed):
        """A single claim with no history should produce no signals."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
            mock_embed.return_value = {"embedding": [0.1] * 768}

            member = Member(
                member_id="EMP001", name="John Doe",
                join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE",
            )
            engine = VectorFraudEngine()

            ctx = AdjudicationContext(
                claim_id="CLM_CURRENT",
                member=member,
                claim_amount=1000.0,
                treatment_date=date(2024, 6, 1),
                extracted_data=ExtractedData(
                    diagnosis="Fever", provider_name="Apollo Clinic"
                ),
            )

            signals = engine.detect(ctx)
            assert not any(
                s.signal_type == "POTENTIAL_DUPLICATE_PATTERN" for s in signals
            )

    @patch("google.generativeai.embed_content")
    def test_potential_duplicate_pattern_triggered(self, mock_embed):
        """Identical embeddings should trigger POTENTIAL_DUPLICATE_PATTERN."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
            # Both calls return the exact same embedding → cosine sim = 1.0
            mock_embed.return_value = {"embedding": [1.0] + [0.0] * 767}

            member = Member(
                member_id="EMP001", name="John Doe",
                join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE",
            )
            engine = VectorFraudEngine()

            # Pre-cache a prior claim with the same embedding
            engine.cache_claim_locally(
                claim_id="CLM_PREV",
                text="Member: EMP001 | Diagnosis: Migraine | Provider: ABC Clinic | Treatment: Consultation | Amount: 4800.0",
                embedding=[1.0] + [0.0] * 767,
            )

            ctx = AdjudicationContext(
                claim_id="CLM_CURRENT",
                member=member,
                claim_amount=4800.0,
                treatment_date=date(2024, 6, 1),
                extracted_data=ExtractedData(
                    diagnosis="Migraine", provider_name="ABC Clinic"
                ),
            )

            signals = engine.detect(ctx)
            dup_signals = [
                s for s in signals
                if s.signal_type == "POTENTIAL_DUPLICATE_PATTERN"
            ]
            assert len(dup_signals) == 1
            assert dup_signals[0].score_impact == 40.0

    @patch("google.generativeai.embed_content")
    def test_near_exact_duplicate_triggered(self, mock_embed):
        """Similarity > 0.99 should also trigger NEAR_EXACT_DUPLICATE_PATTERN."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
            mock_embed.return_value = {"embedding": [1.0] + [0.0] * 767}

            member = Member(
                member_id="EMP001", name="John Doe",
                join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE",
            )
            engine = VectorFraudEngine()

            engine.cache_claim_locally(
                claim_id="CLM_PREV",
                text="Same profile",
                embedding=[1.0] + [0.0] * 767,
            )

            ctx = AdjudicationContext(
                claim_id="CLM_CURRENT",
                member=member,
                claim_amount=4800.0,
                treatment_date=date(2024, 6, 1),
                extracted_data=ExtractedData(
                    diagnosis="Migraine", provider_name="ABC Clinic"
                ),
            )

            signals = engine.detect(ctx)
            near_exact = [
                s for s in signals
                if s.signal_type == "NEAR_EXACT_DUPLICATE_PATTERN"
            ]
            assert len(near_exact) == 1
            assert near_exact[0].score_impact == 30.0

    @patch("google.generativeai.embed_content")
    def test_safety_rule_never_critical_severity(self, mock_embed):
        """Safety rule: Vector signals NEVER have CRITICAL severity."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
            mock_embed.return_value = {"embedding": [1.0] + [0.0] * 767}

            member = Member(
                member_id="EMP001", name="John Doe",
                join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE",
            )
            engine = VectorFraudEngine()

            engine.cache_claim_locally(
                claim_id="CLM_PREV",
                text="Same",
                embedding=[1.0] + [0.0] * 767,
            )

            ctx = AdjudicationContext(
                claim_id="CLM_CURRENT",
                member=member,
                claim_amount=4800.0,
                treatment_date=date(2024, 6, 1),
                extracted_data=ExtractedData(
                    diagnosis="Migraine", provider_name="ABC Clinic"
                ),
            )

            signals = engine.detect(ctx)
            for sig in signals:
                assert sig.engine == FraudEngine.VECTOR_SIMILARITY
                # Safety rule: vector signals are at most HIGH, never CRITICAL
                assert sig.severity != FraudSeverity.CRITICAL, (
                    f"Vector signal {sig.signal_type} has CRITICAL severity, "
                    "violating the safety rule"
                )

    @patch("google.generativeai.embed_content")
    def test_below_threshold_no_signal(self, mock_embed):
        """Claims with similarity < 0.96 should NOT trigger signals."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
            # Different embeddings that won't produce high similarity
            call_count = 0

            def mock_fn(model, content, task_type):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return {"embedding": [1.0, 0.0, 0.0] + [0.0] * 765}
                return {"embedding": [1.0, 0.0, 0.0] + [0.0] * 765}

            mock_embed.side_effect = mock_fn

            member = Member(
                member_id="EMP001", name="John Doe",
                join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE",
            )
            engine = VectorFraudEngine()

            # Cache with a DIFFERENT embedding
            engine.cache_claim_locally(
                claim_id="CLM_PREV",
                text="Different claim",
                embedding=[0.0, 1.0, 0.0] + [0.0] * 765,
            )

            ctx = AdjudicationContext(
                claim_id="CLM_CURRENT",
                member=member,
                claim_amount=1000.0,
                treatment_date=date(2024, 6, 1),
                extracted_data=ExtractedData(
                    diagnosis="Cold", provider_name="Different Clinic"
                ),
            )

            signals = engine.detect(ctx)
            assert not any(
                s.signal_type == "POTENTIAL_DUPLICATE_PATTERN" for s in signals
            )

    def test_no_api_key_returns_empty(self):
        """Without GEMINI_API_KEY, the engine returns no signals."""
        with patch.dict("os.environ", {}, clear=True):
            member = Member(
                member_id="EMP001", name="John Doe",
                join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE",
            )
            engine = VectorFraudEngine()
            ctx = AdjudicationContext(
                claim_id="CLM_CURRENT",
                member=member,
                claim_amount=1000.0,
                treatment_date=date(2024, 6, 1),
                extracted_data=ExtractedData(diagnosis="Fever"),
            )
            signals = engine.detect(ctx)
            assert signals == []

    @patch("google.generativeai.embed_content")
    def test_no_diagnosis_returns_empty(self, mock_embed):
        """Without a diagnosis, the engine skips detection."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
            member = Member(
                member_id="EMP001", name="John Doe",
                join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE",
            )
            engine = VectorFraudEngine()
            ctx = AdjudicationContext(
                claim_id="CLM_CURRENT",
                member=member,
                claim_amount=1000.0,
                treatment_date=date(2024, 6, 1),
                extracted_data=ExtractedData(),  # no diagnosis
            )
            signals = engine.detect(ctx)
            assert signals == []
            mock_embed.assert_not_called()


# ── Fraud Aggregator Tests ────────────────────────────────────────────────

class TestFraudAggregator:
    """Tests for the Fraud Score Aggregator."""

    @patch("google.generativeai.embed_content")
    def test_aggregator_combines_rule_and_vector(self, mock_embed):
        """Aggregator should combine rule-based + vector signals into one score."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
            mock_embed.return_value = {"embedding": [1.0] + [0.0] * 767}

            member = Member(
                member_id="EMP001", name="John Doe",
                join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE",
            )
            aggregator = FraudAggregator()

            # Pre-populate vector engine cache
            aggregator.vector_engine.cache_claim_locally(
                claim_id="CLM_PREV",
                text="Same profile",
                embedding=[1.0] + [0.0] * 767,
            )

            ctx = AdjudicationContext(
                claim_id="CLM_CURRENT",
                member=member,
                claim_amount=1000.0,
                treatment_date=date(2024, 6, 1),
                extracted_data=ExtractedData(
                    diagnosis="Fever", provider_name="Apollo Clinic"
                ),
                previous_claims_count_24h=1,  # triggers Rule 1
            )

            result = aggregator.detect(ctx)

            # Rule 1 gives +20 (MULTIPLE_CLAIMS_24H)
            # Vector gives +40 (POTENTIAL_DUPLICATE_PATTERN) + 30 (NEAR_EXACT) = 70
            # Total = 90.0
            assert result.fraud_score == 90.0
            assert result.requires_manual_review is True
            assert result.details["rule_based_signals"] >= 1
            assert result.details["vector_signals"] >= 1

    @patch("google.generativeai.embed_content")
    def test_aggregator_score_capped_at_100(self, mock_embed):
        """Fraud score should never exceed 100."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": "fake_key"}):
            mock_embed.return_value = {"embedding": [1.0] + [0.0] * 767}

            member = Member(
                member_id="EMP001", name="John Doe",
                join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE",
            )
            aggregator = FraudAggregator()

            aggregator.vector_engine.cache_claim_locally(
                claim_id="CLM_PREV",
                text="Same",
                embedding=[1.0] + [0.0] * 767,
            )

            ctx = AdjudicationContext(
                claim_id="CLM_CURRENT",
                member=member,
                claim_amount=30000.0,  # triggers HIGH_VALUE_CLAIM +15
                treatment_date=date(2024, 6, 1),
                extracted_data=ExtractedData(
                    diagnosis="Fever",
                    provider_name="Apollo Clinic",
                    bill_number="BILL-DUP",
                ),
                previous_claims_count_24h=3,  # triggers HIGH_FREQUENCY +40
            )

            result = aggregator.detect(ctx)
            assert result.fraud_score <= 100.0

    def test_aggregator_zero_score_no_review(self):
        """Clean claim with no fraud signals should have score 0 and no review."""
        with patch.dict("os.environ", {}, clear=True):
            member = Member(
                member_id="EMP001", name="John Doe",
                join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE",
            )
            aggregator = FraudAggregator()
            ctx = AdjudicationContext(
                claim_id="CLM_CLEAN",
                member=member,
                claim_amount=1000.0,
                treatment_date=date(2024, 6, 1),
                extracted_data=ExtractedData(diagnosis="Fever"),
            )
            result = aggregator.detect(ctx)
            assert result.fraud_score == 0.0
            assert result.requires_manual_review is False
            assert len(result.signals) == 0

    def test_aggregator_manual_review_threshold(self):
        """Score >= 70 should trigger manual review."""
        with patch.dict("os.environ", {}, clear=True):
            from app.database import IN_MEMORY_CLAIMS

            member = Member(
                member_id="EMP001", name="John Doe",
                join_date=date(2024, 1, 1), policy_id="POL_OPD_ADVANTAGE",
            )
            aggregator = FraudAggregator()

            # Trigger enough rule-based signals to reach 70
            # Rule 1 HIGH_FREQUENCY = 40, + HIGH_VALUE = 15, + duplicate bill = 60
            IN_MEMORY_CLAIMS["CLM_PREV"] = {
                "claim_id": "CLM_PREV",
                "member_id": "EMP001",
                "treatment_date": date(2024, 6, 1),
                "extracted_data": ExtractedData(
                    diagnosis="Fever", bill_number="BILL-123"
                ),
            }
            IN_MEMORY_CLAIMS["CLM_PREV2"] = {
                "claim_id": "CLM_PREV2",
                "member_id": "EMP001",
                "treatment_date": date(2024, 6, 1),
                "extracted_data": ExtractedData(diagnosis="Cold"),
            }

            ctx = AdjudicationContext(
                claim_id="CLM_CURRENT",
                member=member,
                claim_amount=30000.0,  # +15
                treatment_date=date(2024, 6, 1),
                extracted_data=ExtractedData(
                    diagnosis="Fever", bill_number="BILL-123"
                ),
            )

            result = aggregator.detect(ctx)
            # HIGH_FREQUENCY_CLAIMS_24H (40) + HIGH_VALUE (15) + DUPLICATE_BILL (60) = 100 (capped)
            assert result.fraud_score >= 70.0
            assert result.requires_manual_review is True

            # Cleanup
            IN_MEMORY_CLAIMS.clear()
