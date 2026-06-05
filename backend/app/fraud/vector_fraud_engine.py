"""
Engine 2 — High-Dimensional Vector Fraud Detection (Point 7).

Purpose (from architecture document):
    Detect semantically similar claims that traditional SQL rules
    cannot identify.

Workflow:
    Extracted Claim
        ↓ Fraud Profile Builder
        ↓ Embedding Generation
        ↓ pgvector Storage
        ↓ Similarity Search

Important Safety Rule (from architecture document):
    Vector fraud detection NEVER rejects claims.
    It may only:
        • Increase fraud score
        • Lower confidence
        • Route claim to MANUAL_REVIEW
"""

import os
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import numpy as np
import google.generativeai as genai
from psycopg2.extras import RealDictCursor

from app.models.fraud import FraudSignal, FraudEngine, FraudSeverity
from app.schemas.claim_schema import AdjudicationContext
from app.fraud.fraud_profile import FraudProfileBuilder

logger = logging.getLogger(__name__)

# Similarity threshold from architecture document
SIMILARITY_THRESHOLD = 0.96
# Maximum number of nearest neighbours to retrieve
TOP_K = 5


class VectorFraudEngine:
    """High-dimensional vector fraud detection engine.

    This engine:
    1. Builds a structured fraud profile from the claim context.
    2. Generates an embedding vector via Gemini.
    3. Stores the embedding in pgvector (or a local cache fallback).
    4. Searches for semantically similar historical claims.
    5. If similarity > 0.96, triggers POTENTIAL_DUPLICATE_PATTERN.

    Per the architecture document's safety rule, this engine NEVER
    produces a signal that would reject a claim.  It only increases
    the fraud score, which may route the claim to MANUAL_REVIEW.
    """

    def __init__(self, model_name: str = "models/gemini-embedding-001") -> None:
        self.embedding_model = model_name
        self._local_embeddings_cache: List[Dict[str, Any]] = []
        self._profile_builder = FraudProfileBuilder()
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)

    # ── Embedding Generation ───────────────────────────────────────────────

    def _get_embedding(self, text: str) -> List[float]:
        """Generate an embedding vector for the given text."""
        result = genai.embed_content(
            model=self.embedding_model,
            content=text,
            task_type="retrieval_document",
        )
        emb = result["embedding"]
        # Enforce 768 dimensions to match pgvector schema
        return emb[:768] if len(emb) > 768 else emb

    # ── pgvector Storage & Retrieval ───────────────────────────────────────

    def _search_similar_db(
        self, query_emb: List[float], exclude_claim_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Search for similar claims in PostgreSQL/pgvector."""
        from app.database import get_db_connection

        conn = get_db_connection()
        if not conn:
            return None
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                vector_str = "[" + ",".join(map(str, query_emb)) + "]"
                cur.execute(
                    "SELECT claim_id, similarity, metadata "
                    "FROM search_similar_claims(%s, %s, %s, %s)",
                    (vector_str, SIMILARITY_THRESHOLD, TOP_K, exclude_claim_id),
                )
                rows = cur.fetchall()
                if rows:
                    return [dict(r) for r in rows]
        except Exception as exc:
            logger.warning(
                f"Database vector fraud search failed: {exc}. "
                "Using local cache fallback."
            )
        finally:
            conn.close()
        return None

    def _store_embedding_db(
        self, claim_id: str, embedding: List[float], metadata: Dict[str, Any]
    ) -> bool:
        """Persist an embedding to pgvector.  Returns True on success."""
        import json
        from app.database import get_db_connection

        conn = get_db_connection()
        if not conn:
            return False
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO claim_embeddings (claim_id, embedding, metadata)
                        VALUES (
                            (SELECT id FROM claims WHERE claim_id = %s),
                            %s,
                            %s::jsonb
                        )
                        ON CONFLICT (claim_id) DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            metadata = EXCLUDED.metadata
                        """,
                        (claim_id, embedding, json.dumps(metadata)),
                    )
            return True
        except Exception as exc:
            logger.warning(f"Failed to persist embedding to DB: {exc}")
            return False
        finally:
            conn.close()

    # ── Local Fallback Cache ───────────────────────────────────────────────

    def _search_similar_local(
        self, query_emb: List[float], exclude_claim_id: str
    ) -> List[Dict[str, Any]]:
        """Cosine similarity search over the in-memory embeddings cache."""
        similar: List[Dict[str, Any]] = []
        q_vec = np.array(query_emb)
        norm_q = np.linalg.norm(q_vec)

        for cache_entry in self._local_embeddings_cache:
            if cache_entry["claim_id"] == exclude_claim_id:
                continue
            c_vec = np.array(cache_entry["embedding"])
            norm_c = np.linalg.norm(c_vec)

            similarity = 0.0
            if norm_q > 0 and norm_c > 0:
                similarity = float(np.dot(q_vec, c_vec) / (norm_q * norm_c))

            if similarity >= SIMILARITY_THRESHOLD:
                similar.append(
                    {
                        "claim_id": cache_entry["claim_id"],
                        "similarity": similarity,
                        "metadata": cache_entry["metadata"],
                    }
                )
        similar.sort(key=lambda x: x["similarity"], reverse=True)
        return similar[:TOP_K]

    def cache_claim_locally(
        self,
        claim_id: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Cache an embedding in-memory for local similarity search."""
        self._local_embeddings_cache.append(
            {
                "claim_id": claim_id,
                "text": text,
                "embedding": embedding,
                "metadata": metadata
                or {"text": text, "cached_at": datetime.now(timezone.utc).isoformat()},
            }
        )

    # ── Main Detection Entry Point ─────────────────────────────────────────

    def detect(self, ctx: AdjudicationContext) -> List[FraudSignal]:
        """Run high-dimensional vector fraud detection.

        Returns a list of advisory FraudSignals.  Per the architecture
        safety rule, these signals NEVER directly reject a claim —
        they only increase the fraud score.
        """
        signals: List[FraudSignal] = []

        if not os.getenv("GEMINI_API_KEY"):
            return signals
        if not ctx.extracted_data.diagnosis:
            return signals

        try:
            # Step 1: Build structured fraud profile
            profile_text = self._profile_builder.build_profile_text(ctx)
            profile_metadata = self._profile_builder.build_profile_metadata(ctx)

            # Step 2: Generate embedding
            embedding = self._get_embedding(profile_text)

            # Step 3: Search for similar claims (DB first, fallback to local)
            # Pass None for exclude_claim_id since this claim isn't in DB yet
            similar_claims = self._search_similar_db(embedding, None)
            if similar_claims is None:
                similar_claims = self._search_similar_local(
                    embedding, ctx.claim_id
                )

            # Step 4: Store the embedding (DB + local cache)
            self._store_embedding_db(ctx.claim_id, embedding, profile_metadata)
            self.cache_claim_locally(
                ctx.claim_id, profile_text, embedding, profile_metadata
            )

            # Step 5: Evaluate similarity results
            if similar_claims:
                best_match = similar_claims[0]
                similarity_score = best_match["similarity"]

                # Use the exact signal type from the architecture document:
                # "POTENTIAL_DUPLICATE_PATTERN"
                signals.append(
                    FraudSignal(
                        signal_type="POTENTIAL_DUPLICATE_PATTERN",
                        engine=FraudEngine.VECTOR_SIMILARITY,
                        description=(
                            f"High semantic similarity ({similarity_score:.4f}) "
                            f"detected with claim {best_match['claim_id']}. "
                            f"Diagnosis: {ctx.extracted_data.diagnosis}, "
                            f"Provider: {ctx.extracted_data.provider_name or ctx.hospital_name}."
                        ),
                        # IMPORTANT: severity is HIGH, not CRITICAL.
                        # Vector fraud NEVER directly rejects — it only
                        # increases score and routes to MANUAL_REVIEW.
                        severity=FraudSeverity.HIGH,
                        score_impact=40.0,
                        details={
                            "similar_claim_id": str(best_match["claim_id"]),
                            "similarity_score": similarity_score,
                            "profile_text": profile_text,
                            "matched_metadata": best_match.get("metadata"),
                            "total_similar_claims": len(similar_claims),
                        },
                    )
                )

                # Additional signal for extremely high similarity (> 0.99)
                if similarity_score > 0.99:
                    signals.append(
                        FraudSignal(
                            signal_type="NEAR_EXACT_DUPLICATE_PATTERN",
                            engine=FraudEngine.VECTOR_SIMILARITY,
                            description=(
                                f"Near-exact semantic duplicate ({similarity_score:.4f}) "
                                f"detected with claim {best_match['claim_id']}. "
                                "This strongly suggests a duplicate submission."
                            ),
                            severity=FraudSeverity.HIGH,
                            score_impact=30.0,
                            details={
                                "similar_claim_id": str(best_match["claim_id"]),
                                "similarity_score": similarity_score,
                            },
                        )
                    )

        except Exception as exc:
            logger.error(f"Error during vector fraud detection: {exc}")

        return signals