import os
from typing import List
import google.generativeai as genai

class Embedder:
    def __init__(self, model_name: str = "models/gemini-embedding-001"):
        self.embedding_model = model_name
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)

    def get_embedding(self, text: str) -> List[float]:
        result = genai.embed_content(
            model=self.embedding_model,
            content=text,
            task_type="retrieval_query",
        )
        return result["embedding"]