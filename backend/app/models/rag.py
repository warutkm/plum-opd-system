from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

class RAGQuery(BaseModel):
    question: str
    claim_id: Optional[str] = None

class RAGSource(BaseModel):
    chunk_text: str
    source: str
    similarity: float = 0.0

class RAGResponse(BaseModel):
    answer: str
    sources: List[RAGSource] = Field(default_factory=list)
    confidence: float = 0.0
