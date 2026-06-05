import json
import logging
import os
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from app.schemas.claim_schema import ExtractedData
from app.schemas.decision_schema import MedicalNecessityResult
from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

def is_transient_error(exception: Exception) -> bool:
    err_str = str(exception).lower()
    if any(k in err_str for k in ["429", "quota", "exhausted", "api key", "unauthorized", "invalid key"]):
        return False
    return True

class MedicalNecessityAgent(BaseAgent):
    """
    Medical Necessity AI Agent.
    Evaluates the relationship between the diagnosis and the treatments.
    """

    def __init__(self, model_name: Optional[str] = None) -> None:
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(is_transient_error),
        reraise=True,
    )
    def _call_gemini(self, prompt: str) -> str:
        model = genai.GenerativeModel(self.model_name)
        generation_config = {
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "OBJECT",
                "properties": {
                    "medically_necessary": {"type": "BOOLEAN"},
                    "reasoning": {"type": "STRING"},
                    "confidence": {"type": "NUMBER"},
                },
                "required": ["medically_necessary", "reasoning", "confidence"],
            },
        }
        response = model.generate_content(prompt, generation_config=generation_config)
        return response.text

    def process(self, data: ExtractedData) -> MedicalNecessityResult:
        if not os.getenv("GEMINI_API_KEY"):
            logger.warning("GEMINI_API_KEY not configured. Defaulting medical necessity to True.")
            return MedicalNecessityResult(
                medically_necessary=True,
                reasoning="Gemini API key not configured. Defaulting to True.",
                confidence=1.0,
            )

        prompt = f"""
You are an expert Medical Officer reviewing insurance claims for medical necessity.
Your job is to assess if the diagnosis justifies the treatment, medicines, and diagnostic tests.

Extracted Data:
- Diagnosis: {data.diagnosis}
- Medicines: {data.medicines}
- Tests: {data.tests}
- Procedures: {data.procedures}

Task:
Evaluate whether the prescribed items align with standard clinical protocols for the diagnosis.
- Set medically_necessary to true if they are standard and reasonable.
- Set medically_necessary to false if they are highly unusual or completely unrelated.
- Provide a clear, concise justification of your assessment in the reasoning field.
- Set a confidence score from 0.0 to 1.0 representing your certainty.

Response must be in JSON matching the schema.
"""
        try:
            response_text = self._call_gemini(prompt)
            result = json.loads(response_text)
            return MedicalNecessityResult(
                medically_necessary=result.get("medically_necessary", True),
                reasoning=result.get("reasoning", ""),
                confidence=result.get("confidence", 0.9),
            )
        except Exception as exc:
            logger.error(f"Failed to evaluate medical necessity: {exc}")
            return MedicalNecessityResult(
                medically_necessary=True,
                reasoning=f"Error evaluating necessity: {exc}. Defaulting to True.",
                confidence=0.5,
            )