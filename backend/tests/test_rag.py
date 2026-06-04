"""
Tests for the RAG Policy Assistant (Point 11 from the architecture document).

Verifies:
    1. Chunker reads and splits policy documents.
    2. Local retrieval fallback using cosine similarity works.
    3. Generator generates accurate answers from context.
    4. Generator handles out-of-context questions with the specific fallback message:
       "I am sorry, but the policy documentation provided does not contain enough information to answer this question."
    5. Database seeding runs gracefully when DB is unreachable.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.models.rag import RAGQuery, RAGResponse, RAGSource
from app.rag.document_chunker import DocumentChunker
from app.rag.embedder import Embedder
from app.rag.retriever import Retriever
from app.rag.generator import Generator


# ── Chunker Tests ─────────────────────────────────────────────────────────

def test_document_chunker_extracts_chunks():
    """Verify document chunker reads policy JSON and rules markdown into chunks."""
    chunker = DocumentChunker()
    chunks = chunker.get_chunks()
    
    assert len(chunks) > 0
    for chunk in chunks:
        assert "text" in chunk
        assert "source" in chunk
        assert "index" in chunk
        assert "embedding" in chunk
        assert chunk["source"] in ["policy_terms.json", "adjudication_rules.md"]


# ── Retriever Tests ───────────────────────────────────────────────────────

def test_retriever_local_search_fallback():
    """Verify local retriever returns sorted top chunks using cosine similarity."""
    retriever = Retriever()
    
    # Mock embedder to avoid network call
    mock_query_emb = [0.1] * 768
    
    with patch.object(retriever.embedder, "get_embedding") as mock_embed:
        mock_embed.return_value = [0.1] * 768
        
        # We also mock search_database to return None (triggering local search)
        with patch.object(retriever, "search_database", return_value=None):
            sources = retriever.search_local(mock_query_emb)
            
            assert len(sources) > 0
            assert len(sources) <= 5
            # Results must be sorted in descending order of similarity
            for i in range(len(sources) - 1):
                assert sources[i].similarity >= sources[i+1].similarity


# ── Generator (RAG) Tests ─────────────────────────────────────────────────

def test_generator_ask_with_answer_in_context():
    """Verify generator answers a valid policy question using context chunks."""
    generator = Generator()
    query = RAGQuery(question="What is the annual OPD claim limit?")
    
    # Mock retrieved sources
    mock_sources = [
        RAGSource(
            chunk_text="OPD claim limit is capped at 15000 per member per policy year.",
            source="policy_terms.json",
            similarity=0.95
        )
    ]
    
    # Mock Gemini generative model call and environment variable
    with patch.dict("os.environ", {"GEMINI_API_KEY": "mocked_gemini_key"}), \
         patch("google.generativeai.GenerativeModel") as mock_model_class:
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "The annual OPD claim limit is capped at 15,000 per member per policy year."
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        with patch.object(generator.retriever, "search_database", return_value=None), \
             patch.object(generator.retriever, "search_local", return_value=mock_sources), \
             patch.object(generator.embedder, "get_embedding", return_value=[0.1]*768):
            
            response = generator.ask(query)
            
            assert isinstance(response, RAGResponse)
            assert "15,000" in response.answer
            assert len(response.sources) == 1
            assert response.sources[0].source == "policy_terms.json"
            assert response.confidence == 0.95


def test_generator_ask_with_answer_not_in_context():
    """Verify generator returns the specific fallback message when question is out-of-context."""
    generator = Generator()
    query = RAGQuery(question="Who is the CEO of Plum?")
    
    # Mock retrieved sources (contain irrelevant info)
    mock_sources = [
        RAGSource(
            chunk_text="OPD claims require medical bills and doctor prescriptions.",
            source="adjudication_rules.md",
            similarity=0.32
        )
    ]
    
    fallback_message = "I am sorry, but the policy documentation provided does not contain enough information to answer this question."
    
    with patch.dict("os.environ", {"GEMINI_API_KEY": "mocked_gemini_key"}), \
         patch("google.generativeai.GenerativeModel") as mock_model_class:
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = fallback_message
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        with patch.object(generator.retriever, "search_database", return_value=None), \
             patch.object(generator.retriever, "search_local", return_value=mock_sources), \
             patch.object(generator.embedder, "get_embedding", return_value=[0.1]*768):
            
            response = generator.ask(query)
            
            assert response.answer == fallback_message


# ── Seeding Resilience Tests ──────────────────────────────────────────────

def test_retriever_database_seeding_unreachable_db():
    """Verify database seeding catches connection errors and fails/skips gracefully without throwing."""
    retriever = Retriever()
    
    # Force a connection error by setting DATABASE_URL to a bad host/port
    with patch.dict("os.environ", {"DATABASE_URL": "postgresql://postgres:postgres@invalidhost:5432/postgres"}):
        # This call must NOT raise any exceptions
        retriever.seed_policy_embeddings()
