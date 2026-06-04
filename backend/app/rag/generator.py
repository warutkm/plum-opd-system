import os
import logging
import google.generativeai as genai

from app.models.rag import RAGQuery, RAGResponse
from app.rag.embedder import Embedder
from app.rag.retriever import Retriever

logger = logging.getLogger(__name__)

class Generator:
    def __init__(self, model_name: str = "gemini-2.5-flash-lite"):
        self.model_name = model_name
        self.embedder = Embedder()
        self.retriever = Retriever()

    def ask(self, query: RAGQuery) -> RAGResponse:
        if not os.getenv("GEMINI_API_KEY"):
            return RAGResponse(
                answer="Gemini API key is not configured. Policy assistant cannot respond.",
                sources=[],
                confidence=0.0,
            )
        try:
            query_emb = self.embedder.get_embedding(query.question)
            sources = self.retriever.search_database(query_emb)
            if sources is None:
                sources = self.retriever.search_local(query_emb)
            
            if not sources:
                return RAGResponse(
                    answer="I could not find any policy terms to answer your question.",
                    sources=[],
                    confidence=0.0,
                )

            model = genai.GenerativeModel(self.model_name)
            context = "\n\n".join([f"[{src.source}]:\n{src.chunk_text}" for src in sources])

            prompt = f"""
You are the Plum OPD Policy Assistant. Your task is to answer the user's question about the OPD insurance policy based ONLY on the documentation context provided below.

Rules:
1. Provide a professional, helpful, and highly accurate answer.
2. Rely ONLY on the facts mentioned in the context. Do not invent details.
3. If the answer cannot be determined from the context, state: "I am sorry, but the policy documentation provided does not contain enough information to answer this question."

Context Chunks:
{context}

Question: {query.question}
"""
            response = model.generate_content(prompt)
            avg_similarity = sum(src.similarity for src in sources) / len(sources)

            return RAGResponse(
                answer=response.text.strip(),
                sources=sources,
                confidence=avg_similarity,
            )
        except Exception as exc:
            logger.error(f"RAG Policy Assistant error: {exc}")
            return RAGResponse(
                answer=f"An error occurred while answering your question: {exc}",
                sources=[],
                confidence=0.0,
            )