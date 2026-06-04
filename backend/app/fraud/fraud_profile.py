"""
Fraud Profile Builder — Point 7, Engine 2 from the architecture document.

Converts extracted claim data into a structured text profile optimized
for embedding generation.  The profile is a deterministic, reproducible
string that captures the key semantic axes an embedding model should
differentiate on:

    Diagnosis | Provider | Treatment | Amount

This sits between extraction and embedding in the pipeline:

    Extracted Claim → Fraud Profile Builder → Embedding Generation
                       → pgvector Storage → Similarity Search
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from app.schemas.claim_schema import AdjudicationContext, ExtractedData


class FraudProfileBuilder:
    """Builds a structured fraud profile string from claim data.

    The profile follows the format specified in the architecture document:
        Diagnosis: <diagnosis>
        Provider: <provider>
        Treatment: <treatment>
        Amount: <amount>

    This structured profile is then embedded via the Gemini embedding
    model and stored in pgvector for semantic similarity search.
    """

    @staticmethod
    def build_profile_text(ctx: AdjudicationContext) -> str:
        """Build a structured fraud profile string from adjudication context.

        Parameters
        ----------
        ctx : AdjudicationContext
            The full claim context including extracted data.

        Returns
        -------
        str
            A deterministic, structured profile string suitable for
            embedding generation.
        """
        ed = ctx.extracted_data or ExtractedData()

        diagnosis = (ed.diagnosis or "Unknown").strip()
        provider = (
            ed.provider_name or ctx.hospital_name or "Unknown"
        ).strip()

        # Treatment is derived from procedures, tests, and medicines
        treatments = []
        if ed.procedures:
            treatments.extend(ed.procedures)
        if ed.tests:
            treatments.extend(ed.tests)
        if not treatments and ed.medicines:
            treatments.append("Pharmacy")
        if not treatments:
            treatments.append("Consultation")
        treatment_str = ", ".join(treatments)

        amount = ctx.claim_amount

        # Build the profile as specified in architecture doc
        profile_lines = [
            f"Diagnosis: {diagnosis}",
            f"Provider: {provider}",
            f"Treatment: {treatment_str}",
            f"Amount: {amount}",
        ]

        # Include member context for stronger duplicate detection
        profile_lines.insert(0, f"Member: {ctx.member.member_id}")

        return " | ".join(profile_lines)

    @staticmethod
    def build_profile_metadata(ctx: AdjudicationContext) -> Dict[str, Any]:
        """Build a metadata dictionary for the claim embedding record.

        This metadata is stored alongside the embedding vector in
        pgvector for post-retrieval analysis (e.g. showing the
        adjuster which fields matched).
        """
        ed = ctx.extracted_data or ExtractedData()

        return {
            "claim_id": ctx.claim_id,
            "member_id": ctx.member.member_id,
            "diagnosis": ed.diagnosis,
            "provider": ed.provider_name or ctx.hospital_name,
            "procedures": ed.procedures,
            "tests": ed.tests,
            "medicines": ed.medicines,
            "amount": ctx.claim_amount,
            "treatment_date": str(ctx.treatment_date),
        }