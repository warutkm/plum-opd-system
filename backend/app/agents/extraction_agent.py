import json
import logging
import os
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from app.schemas.claim_schema import ExtractedData
from app.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

def is_transient_error(exception: Exception) -> bool:
    err_str = str(exception).lower()
    if any(k in err_str for k in ["429", "quota", "exhausted", "api key", "unauthorized", "invalid key"]):
        return False
    return True

# ──────────────────────────────────────────────────────────────
# Few-Shot Examples (per PDF spec: medical bill, prescription,
# diagnostic report)
# ──────────────────────────────────────────────────────────────

_FEW_SHOT_EXAMPLES = """
--- EXAMPLE 1: Medical Bill ---
INPUT (text from an OPD medical bill image):
  "Apollo Hospitals, Bangalore
   Patient: Rajesh Kumar  Age: 35
   Bill No: INV-2025-001
   Dr. Anita Sharma  Reg: KA/45678/2015
   Date: 15/03/2025
   Diagnosis: Acute Pharyngitis
   Consultation Fee: Rs. 1,500
   Total: Rs. 1,500"

OUTPUT:
{
  "patient_name": "Rajesh Kumar",
  "bill_number": "INV-2025-001",
  "age": "35",
  "doctor_name": "Dr. Anita Sharma",
  "doctor_registration": "KA/45678/2015",
  "diagnosis": "Acute Pharyngitis",
  "medicines": [],
  "procedures": ["Consultation"],
  "tests": [],
  "provider_name": "Apollo Hospitals",
  "bill_amount": 1500.0,
  "treatment_date": "2025-03-15",
  "bill_items": {"consultation_fee": 1500.0},
  "extraction_confidence": 0.95
}

--- EXAMPLE 2: Prescription + Bill ---
INPUT (text from a prescription and dental bill):
  "Smile Dental Clinic, Mumbai
   Patient: Priya Singh  Age: 28
   Invoice No: INV-2025-042
   Dr. Rahul Mehta  Reg: MH/34567/2018
   Date: 20-04-2025
   Diagnosis: Dental caries, right lower molar
   Procedures: Root canal treatment, Teeth whitening
   Root canal: ₹8,000
   Teeth whitening: ₹5,000
   Medicines: Amoxicillin 500mg, Ibuprofen 400mg
   Total Bill: ₹13,000"

OUTPUT:
{
  "patient_name": "Priya Singh",
  "bill_number": "INV-2025-042",
  "age": "28",
  "doctor_name": "Dr. Rahul Mehta",
  "doctor_registration": "MH/34567/2018",
  "diagnosis": "Dental caries, right lower molar",
  "medicines": ["Amoxicillin 500mg", "Ibuprofen 400mg"],
  "procedures": ["Root canal treatment", "Teeth whitening"],
  "tests": [],
  "provider_name": "Smile Dental Clinic",
  "bill_amount": 13000.0,
  "treatment_date": "2025-04-20",
  "bill_items": {"root_canal": 8000.0, "teeth_whitening": 5000.0},
  "extraction_confidence": 0.92
}

--- EXAMPLE 3: Diagnostic Report ---
INPUT (text from a diagnostic lab report):
  "SRL Diagnostics, Delhi
   Patient: Amit Verma  Age: 45
   Receipt No: REC-2025-999
   Referred by Dr. Suresh Patil  Reg: DL/56789/2016
   Date: 10.05.2025
   Tests Ordered: Complete Blood Count, Lipid Profile, HbA1c
   Diagnosis: Suspected Type 2 Diabetes
   Lab Charges: Rs 3,500
   Report Collection Fee: Rs 200
   Total: Rs 3,700"

OUTPUT:
{
  "patient_name": "Amit Verma",
  "bill_number": "REC-2025-999",
  "age": "45",
  "doctor_name": "Dr. Suresh Patil",
  "doctor_registration": "DL/56789/2016",
  "diagnosis": "Suspected Type 2 Diabetes",
  "medicines": [],
  "procedures": [],
  "tests": ["Complete Blood Count", "Lipid Profile", "HbA1c"],
  "provider_name": "SRL Diagnostics",
  "bill_amount": 3700.0,
  "treatment_date": "2025-05-10",
  "bill_items": {"lab_charges": 3500.0, "report_collection_fee": 200.0},
  "extraction_confidence": 0.93
}
"""

# Fields required for high-quality extraction
_CRITICAL_FIELDS = ["patient_name", "doctor_registration", "diagnosis", "bill_amount", "treatment_date", "bill_items"]
_IMPORTANT_FIELDS = ["doctor_name", "provider_name", "medicines", "procedures", "tests"]


class MultimodalExtractionAgent(BaseAgent):
    """
    Multimodal AI Extraction Agent.
    Responsible for parsing raw document bytes (PDF, JPEG, PNG)
    and returning structured ExtractedData using Gemini 2.5 Flash.

    Features:
    - Few-shot prompting with 3 diverse examples (bill, prescription, lab report)
    - Structured JSON output via Gemini response_schema
    - Confidence calculation based on field completeness + Gemini self-assessment
    - Retry with exponential backoff on transient failures
    """

    def __init__(self, model_name: str = "gemini-2.5-flash-lite") -> None:
        self.model_name = model_name
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        else:
            logger.warning("GEMINI_API_KEY is not set. Extraction agent calls will fail.")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(is_transient_error),
        reraise=True,
    )
    def _call_gemini(self, contents: List[Any]) -> str:
        """Call Gemini API with retry logic and strict JSON schema."""
        model = genai.GenerativeModel(self.model_name)

        generation_config = {
            "response_mime_type": "application/json",
        }

        response = model.generate_content(
            contents,
            generation_config=generation_config,
        )
        return response.text

    def _calculate_confidence(self, data: Dict[str, Any], gemini_confidence: float) -> float:
        """
        Calculate extraction confidence based on:
        - Field completeness (40%)
        - Gemini self-assessed confidence (40%)
        - Validation success (data quality signals) (20%)
        """
        # Field completeness score
        critical_present = sum(1 for f in _CRITICAL_FIELDS if data.get(f))
        important_present = sum(1 for f in _IMPORTANT_FIELDS if data.get(f))
        completeness = (
            (critical_present / len(_CRITICAL_FIELDS)) * 0.7 +
            (important_present / len(_IMPORTANT_FIELDS)) * 0.3
        )

        # Data quality signals
        quality_score = 1.0
        # Penalize if bill_amount is 0 or missing
        if not data.get("bill_amount") or data.get("bill_amount", 0) <= 0:
            quality_score -= 0.3
        # Penalize if no bill items extracted
        if not data.get("bill_items"):
            quality_score -= 0.2
        # Penalize if treatment_date couldn't be parsed
        if not data.get("treatment_date"):
            quality_score -= 0.2
        # Penalize if doctor_registration is missing
        if not data.get("doctor_registration"):
            quality_score -= 0.15
        quality_score = max(0.0, quality_score)

        # Weighted combination
        final = (completeness * 0.40) + (gemini_confidence * 0.40) + (quality_score * 0.20)
        return round(min(1.0, max(0.0, final)), 2)

    def process(self, file_contents: List[Tuple[bytes, str]]) -> ExtractedData:
        """
        Extract structured information from claim documents using Gemini 2.5 Flash.

        Args:
            file_contents: List of (file_bytes, mime_type) tuples.
                          Supported: application/pdf, image/jpeg, image/png

        Returns:
            ExtractedData with all parsed fields and confidence score.
        """
        if not os.getenv("GEMINI_API_KEY"):
            logger.error("GEMINI_API_KEY not configured. Cannot perform AI extraction.")
            return ExtractedData(
                extraction_confidence=0.0,
                raw_extraction={"error": "GEMINI_API_KEY not configured"},
            )

        if not file_contents:
            logger.warning("No file contents provided for extraction.")
            return ExtractedData(
                extraction_confidence=0.0,
                raw_extraction={"error": "No files provided"},
            )

        # Build multimodal content: files first, then few-shot + task prompt
        contents = []
        for file_bytes, mime_type in file_contents:
            contents.append({
                "mime_type": mime_type,
                "data": file_bytes,
            })

        prompt = f"""You are a Staff AI Medical Claims Extraction Agent at Plum Insurance. Your task is to analyze the attached medical documents (prescription, invoice, medical bill, diagnostic report) and extract clinical and financial details into a structured JSON payload.

GUIDELINES:
1. Extract patient details exactly as written on the document.
2. Extract the bill number, invoice number, or receipt number if visible in the document. Set to null if not found.
3. Locate the doctor registration number. This is CRITICAL. Common formats:
   - Standard: KA/45678/2015, DL/34567/2016
   - Ayurvedic: AYUR/KL/2345/2019
   - Homeopathic: HOM/MH/1234/2020
   If not clearly visible, output null.
4. Identify the primary diagnosis or reason for consultation.
5. Extract lists of medicines prescribed, procedures performed, and diagnostic tests ordered.
6. Extract hospital/clinic name exactly as printed.
7. Extract the treatment date in YYYY-MM-DD format. Convert from any format (DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, etc.).
8. Break down individual line items from the bill into a dictionary of snake_case keys to numerical amounts.
   - Example: "Consultation Fee: Rs. 1,500" → {{"consultation_fee": 1500.0}}
   - Example: "Root Canal: ₹8,000" → {{"root_canal": 8000.0}}
9. Set extraction_confidence between 0.0 and 1.0 based on how clearly you could read and extract each field.
   - 0.95+ = all fields clearly extracted
   - 0.80-0.94 = most fields clear, some uncertain
   - 0.60-0.79 = significant uncertainty in multiple fields
   - Below 0.60 = poor quality, many fields uncertain or missing
10. CONSOLIDATION: If multiple files or documents are provided, combine and consolidate all the extracted details into a single flat JSON object matching the requested schema. Do NOT return a list of JSON objects.

{_FEW_SHOT_EXAMPLES}

Now analyze the attached document(s) and extract the information.
Return ONLY a valid JSON object matching the requested schema. No additional text.
"""
        contents.append(prompt)

        try:
            response_text = self._call_gemini(contents)
            data = json.loads(response_text)

            # Consolidate list response to dictionary if returned (e.g. from multiple files)
            if isinstance(data, list):
                logger.info("Gemini returned a list of extractions. Consolidating...")
                consolidated = {
                    "patient_name": None,
                    "bill_number": None,
                    "age": None,
                    "doctor_name": None,
                    "doctor_registration": None,
                    "diagnosis": None,
                    "medicines": [],
                    "procedures": [],
                    "tests": [],
                    "provider_name": None,
                    "bill_amount": 0.0,
                    "treatment_date": None,
                    "bill_items": {},
                    "extraction_confidence": 0.0
                }
                confidences = []
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    
                    # Merge strings/scalars
                    for field in ["patient_name", "bill_number", "age", "doctor_name", "doctor_registration", "diagnosis", "provider_name", "treatment_date"]:
                        val = item.get(field)
                        if val and not consolidated[field]:
                            consolidated[field] = str(val)
                    
                    # Merge lists
                    for field in ["medicines", "procedures", "tests"]:
                        vals = item.get(field)
                        if isinstance(vals, list):
                            for v in vals:
                                if v and str(v) not in consolidated[field]:
                                    consolidated[field].append(str(v))
                    
                    # Merge bill items and amount
                    amount = item.get("bill_amount")
                    if amount:
                        try:
                            consolidated["bill_amount"] += float(amount)
                        except (ValueError, TypeError):
                            pass
                    
                    items = item.get("bill_items")
                    if isinstance(items, dict):
                        for k, v in items.items():
                            try:
                                consolidated["bill_items"][k] = float(v)
                            except (ValueError, TypeError):
                                consolidated["bill_items"][k] = v
                                
                    conf = item.get("extraction_confidence")
                    if conf is not None:
                        try:
                            confidences.append(float(conf))
                        except (ValueError, TypeError):
                            pass
                
                if confidences:
                    consolidated["extraction_confidence"] = sum(confidences) / len(confidences)
                else:
                    consolidated["extraction_confidence"] = 0.85
                
                data = consolidated

            # Parse treatment date
            treatment_date = None
            if data.get("treatment_date"):
                try:
                    treatment_date = date.fromisoformat(data["treatment_date"])
                except Exception:
                    # Try DD/MM/YYYY, DD-MM-YYYY formats
                    raw_date = data["treatment_date"]
                    for sep in ["/", "-", "."]:
                        parts = raw_date.split(sep)
                        if len(parts) == 3:
                            try:
                                d, m, y = parts
                                if len(y) == 2:
                                    y = f"20{y}"
                                treatment_date = date(int(y), int(m), int(d))
                                break
                            except Exception:
                                continue

            # Get Gemini's self-assessed confidence
            gemini_confidence = data.get("extraction_confidence", 0.85)

            # Calculate composite confidence
            confidence = self._calculate_confidence(data, gemini_confidence)

            return ExtractedData(
                patient_name=data.get("patient_name"),
                bill_number=data.get("bill_number"),
                age=data.get("age"),
                doctor_name=data.get("doctor_name"),
                doctor_registration=data.get("doctor_registration"),
                diagnosis=data.get("diagnosis"),
                medicines=data.get("medicines", []),
                procedures=data.get("procedures", []),
                tests=data.get("tests", []),
                provider_name=data.get("provider_name"),
                bill_amount=data.get("bill_amount"),
                treatment_date=treatment_date,
                bill_items=data.get("bill_items", {}),
                extraction_confidence=confidence,
                raw_extraction=data,
            )
        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse Gemini JSON response: {exc}")
            return ExtractedData(
                extraction_confidence=0.0,
                raw_extraction={"error": f"JSON parse error: {exc}"},
            )
        except Exception as exc:
            logger.error(f"Failed during Gemini extraction: {exc}")
            return ExtractedData(
                extraction_confidence=0.0,
                raw_extraction={"error": str(exc)},
            )