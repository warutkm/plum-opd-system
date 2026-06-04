import os
import logging
import numpy as np
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Optional

from app.models.rag import RAGSource
from app.rag.document_chunker import DocumentChunker
from app.rag.embedder import Embedder

logger = logging.getLogger(__name__)

class Retriever:
    def __init__(self):
        self.chunker = DocumentChunker()
        self.embedder = Embedder()

    def search_database(self, query_emb: List[float]) -> Optional[List[RAGSource]]:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            return None
        try:
            conn = psycopg2.connect(db_url, connect_timeout=3)
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    vector_str = "[" + ",".join(map(str, query_emb)) + "]"
                    cur.execute(
                        "SELECT chunk_text, chunk_source, similarity FROM search_policy_chunks(%s, 5, 0.3)",
                        (vector_str,),
                    )
                    rows = cur.fetchall()
                    if rows:
                        return [
                            RAGSource(chunk_text=r["chunk_text"], source=r["chunk_source"], similarity=float(r["similarity"]))
                            for r in rows
                        ]
            finally:
                conn.close()
        except Exception as exc:
            logger.warning(f"Database vector search failed: {exc}. Falling back to local RAG.")
        return None

    def search_local(self, query_emb: List[float]) -> List[RAGSource]:
        chunks = self.chunker.get_chunks()
        if not chunks:
            return []

        if not os.getenv("GEMINI_API_KEY"):
            logger.warning("GEMINI_API_KEY not configured. Using keyword lookup fallback.")
            return [RAGSource(chunk_text=c["text"], source=c["source"], similarity=0.5) for c in chunks[:5]]

        for chunk in chunks:
            if chunk["embedding"] is None:
                try:
                    chunk["embedding"] = self.embedder.get_embedding(chunk["text"])
                except Exception as exc:
                    logger.error(f"Failed to embed chunk: {exc}")
                    chunk["embedding"] = [0.0] * 768

        results = []
        q_vec = np.array(query_emb)
        for chunk in chunks:
            c_vec = np.array(chunk["embedding"])
            norm_q = np.linalg.norm(q_vec)
            norm_c = np.linalg.norm(c_vec)
            if norm_q > 0 and norm_c > 0:
                sim = float(np.dot(q_vec, c_vec) / (norm_q * norm_c))
            else:
                sim = 0.0
            results.append((sim, chunk))

        results.sort(key=lambda x: x[0], reverse=True)
        return [RAGSource(chunk_text=r[1]["text"], source=r[1]["source"], similarity=r[0]) for r in results[:5]]

    def seed_policy_embeddings(self) -> None:
        """Seed policy_embeddings table in the database if it is empty."""
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            logger.info("DATABASE_URL not configured. Skipping database RAG seeding.")
            return

        try:
            conn = psycopg2.connect(db_url, connect_timeout=3)
            try:
                with conn:
                    with conn.cursor() as cur:
                        # Check if already seeded
                        cur.execute("SELECT COUNT(*) FROM policy_embeddings")
                        row = cur.fetchone()
                        count = 0
                        if row:
                            if isinstance(row, dict):
                                count = list(row.values())[0]
                            else:
                                count = row[0]
                        
                        if count > 0:
                            logger.info(f"policy_embeddings already contains {count} chunks. Skipping seeding.")
                            return
                        
                        logger.info("policy_embeddings table is empty. Generating and seeding chunks...")
                        chunks = self.chunker.get_chunks()
                        if not chunks:
                            logger.warning("No policy chunks found to seed.")
                            return

                        # Pre-generate embeddings for all chunks
                        for chunk in chunks:
                            emb = self.embedder.get_embedding(chunk["text"])
                            vector_str = "[" + ",".join(map(str, emb)) + "]"
                            
                            # Retrieve a policy ID if exists
                            cur.execute("SELECT id FROM policies LIMIT 1")
                            policy_row = cur.fetchone()
                            policy_uuid = None
                            if policy_row:
                                if isinstance(policy_row, dict):
                                    policy_uuid = policy_row.get("id")
                                else:
                                    policy_uuid = policy_row[0]

                            cur.execute(
                                """
                                INSERT INTO policy_embeddings (policy_id, chunk_text, chunk_source, chunk_index, embedding)
                                VALUES (%s, %s, %s, %s, %s)
                                """,
                                (policy_uuid, chunk["text"], chunk["source"], chunk["index"], vector_str),
                            )
                        logger.info(f"Successfully seeded {len(chunks)} policy chunks into database.")
            finally:
                conn.close()
        except Exception as exc:
            logger.warning(f"Failed to seed policy embeddings in database: {exc}")