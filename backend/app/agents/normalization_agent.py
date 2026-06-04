"""
Phase 2B: Data Normalization Agent

Responsibilities per PDF spec:
  - Date Normalization:       01/11/24 → 2024-11-01
  - Doctor Reg Normalization: ka-12345-2015 → KA/12345/2015
  - Amount Normalization:     ₹5,000 → 5000.0
  - Provider Normalization:   Apollo Hosp. → Apollo Hospitals
  - Bill key standardization: "Consultation Fee" → "consultation_fee"
"""

import re
import time
from datetime import date
from typing import Dict, Any, List, Optional, Tuple

from app.agents.base_agent import BaseAgent
from app.models.audit import AuditTraceEntry
from app.schemas.claim_schema import ExtractedData


# ──────────────────────────────────────────────────────────────
# Provider name aliases → canonical names
# ──────────────────────────────────────────────────────────────

_PROVIDER_ALIASES: Dict[str, str] = {
    "apollo": "Apollo Hospitals",
    "apollo hosp": "Apollo Hospitals",
    "apollo hospitals": "Apollo Hospitals",
    "apollo clinic": "Apollo Hospitals",
    "fortis": "Fortis Healthcare",
    "fortis hosp": "Fortis Healthcare",
    "fortis healthcare": "Fortis Healthcare",
    "max": "Max Healthcare",
    "max hosp": "Max Healthcare",
    "max healthcare": "Max Healthcare",
    "manipal": "Manipal Hospitals",
    "manipal hosp": "Manipal Hospitals",
    "manipal hospitals": "Manipal Hospitals",
    "narayana": "Narayana Health",
    "narayana hosp": "Narayana Health",
    "narayana health": "Narayana Health",
}


def _normalize_date(raw: str) -> Optional[date]:
    """
    Normalize date strings from various Indian formats.
    Handles: DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY, DD/MM/YY, YYYY-MM-DD
    """
    if not raw:
        return None
    raw = raw.strip()

    # Already ISO format
    try:
        return date.fromisoformat(raw)
    except ValueError:
        pass

    # Try common separators
    for sep in ["/", "-", "."]:
        parts = raw.split(sep)
        if len(parts) == 3:
            try:
                a, b, c = parts
                # DD/MM/YYYY or DD-MM-YYYY
                if len(c) == 4:
                    return date(int(c), int(b), int(a))
                # DD/MM/YY → DD/MM/20YY
                elif len(c) == 2:
                    year = 2000 + int(c) if int(c) < 50 else 1900 + int(c)
                    return date(year, int(b), int(a))
                # YYYY/MM/DD (some systems)
                elif len(a) == 4:
                    return date(int(a), int(b), int(c))
            except (ValueError, TypeError):
                continue

    return None


def _normalize_doctor_registration(raw: str) -> str:
    """
    Normalize doctor registration number formats.
    ka-12345-2015 → KA/12345/2015
    AYUR-KL-2345-2019 → AYUR/KL/2345/2019
    HOM MH 1234 2020 → HOM/MH/1234/2020
    """
    if not raw:
        return raw
    # Strip and uppercase
    cleaned = raw.strip().upper()
    # Replace common separators (-, space, \) with /
    cleaned = re.sub(r"[\-\s\\]+", "/", cleaned)
    # Remove doubled slashes
    cleaned = re.sub(r"/+", "/", cleaned)
    # Strip trailing/leading slashes
    cleaned = cleaned.strip("/")
    return cleaned


def _normalize_amount(raw: Any) -> Optional[float]:
    """
    Normalize currency amounts.
    ₹5,000 → 5000.0
    Rs. 1,500 → 1500.0
    INR 2000 → 2000.0
    """
    if isinstance(raw, (int, float)):
        return float(raw)
    if not isinstance(raw, str):
        return None
    # Remove currency symbols and text
    cleaned = raw.strip()
    cleaned = re.sub(r"[₹$]", "", cleaned)
    cleaned = re.sub(r"(?i)^(rs\.?|inr)\s*", "", cleaned)
    # Remove commas and spaces
    cleaned = cleaned.replace(",", "").replace(" ", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_provider(raw: str, network_hospitals: List[str] = None) -> str:
    """
    Normalize provider/hospital names using fuzzy matching against known names.
    "Apollo Hosp." → "Apollo Hospitals"
    """
    if not raw:
        return raw
    cleaned = raw.strip()
    # Remove trailing dots and common abbreviations
    cleaned = re.sub(r"\.\s*$", "", cleaned)

    # Try exact alias match
    lookup = cleaned.lower().rstrip(".")
    if lookup in _PROVIDER_ALIASES:
        return _PROVIDER_ALIASES[lookup]

    # Try fuzzy substring match against network hospitals
    if network_hospitals:
        name_lower = cleaned.lower()
        for hosp in network_hospitals:
            hosp_lower = hosp.lower()
            # If the raw name is a substring of a known hospital
            if name_lower in hosp_lower or hosp_lower in name_lower:
                return hosp
            # If significant overlap (first word match)
            raw_first = name_lower.split()[0] if name_lower.split() else ""
            hosp_first = hosp_lower.split()[0] if hosp_lower.split() else ""
            if raw_first and raw_first == hosp_first and len(raw_first) > 3:
                return hosp

    # Return title-cased version
    return cleaned.title()


class NormalizationAgent(BaseAgent):
    """
    Phase 2B: Data Normalization Agent

    Normalizes extracted data fields to canonical formats before
    they reach the deterministic rule engine.
    """

    def __init__(self, network_hospitals: List[str] = None):
        self.network_hospitals = network_hospitals or []

    def process(
        self,
        extracted_data: ExtractedData,
        pre_bill_items: Optional[Dict[str, float]] = None,
    ) -> Tuple[str, Dict[str, Any], AuditTraceEntry]:
        start = time.time()
        norm_status = "PASS"
        norm_details: Dict[str, Any] = {}
        changes: Dict[str, Any] = {}

        # ── Date Normalization ──────────────────────────────────
        if extracted_data.treatment_date is None and extracted_data.raw_extraction.get("treatment_date"):
            raw_date = extracted_data.raw_extraction["treatment_date"]
            parsed = _normalize_date(raw_date)
            if parsed:
                extracted_data.treatment_date = parsed
                changes["treatment_date"] = {"raw": raw_date, "normalized": parsed.isoformat()}

        # ── Doctor Registration Normalization ───────────────────
        doc_reg = extracted_data.doctor_registration
        if doc_reg:
            normalized_reg = _normalize_doctor_registration(doc_reg)
            if normalized_reg != doc_reg:
                changes["doctor_registration"] = {"raw": doc_reg, "normalized": normalized_reg}
            extracted_data.doctor_registration = normalized_reg
            norm_details["doctor_registration"] = normalized_reg

        # ── Amount Normalization ────────────────────────────────
        if extracted_data.bill_amount is not None:
            raw_amt = extracted_data.bill_amount
            if isinstance(raw_amt, str):
                normalized_amt = _normalize_amount(raw_amt)
                if normalized_amt is not None:
                    changes["bill_amount"] = {"raw": raw_amt, "normalized": normalized_amt}
                    extracted_data.bill_amount = normalized_amt

        # ── Provider Normalization ──────────────────────────────
        provider = extracted_data.provider_name
        if provider:
            normalized_provider = _normalize_provider(provider, self.network_hospitals)
            if normalized_provider != provider:
                changes["provider_name"] = {"raw": provider, "normalized": normalized_provider}
            extracted_data.provider_name = normalized_provider
            norm_details["provider_name"] = normalized_provider

        # ── Bill Items Key Standardization ──────────────────────
        source_items = pre_bill_items or extracted_data.bill_items
        standardized_items: Dict[str, float] = {}
        for k, v in (source_items or {}).items():
            clean_k = k.lower().strip().replace(" ", "_").replace("-", "_")
            # Normalize the amount value too
            if isinstance(v, str):
                amt = _normalize_amount(v)
                standardized_items[clean_k] = amt if amt is not None else 0.0
            else:
                standardized_items[clean_k] = float(v)
        extracted_data.bill_items = standardized_items
        norm_details["bill_items_count"] = len(standardized_items)

        # ── Medicine Name Normalization ─────────────────────────
        # Standardize medicine names (trim, title-case)
        if extracted_data.medicines:
            extracted_data.medicines = [m.strip().title() for m in extracted_data.medicines if m.strip()]

        # ── Procedure Name Normalization ────────────────────────
        # Standardize procedure names (trim, title-case)
        if extracted_data.procedures:
            extracted_data.procedures = [p.strip().title() for p in extracted_data.procedures if p.strip()]

        # Store normalization changes for audit
        extracted_data.normalized_data = changes
        norm_details["changes_made"] = len(changes)

        if not changes:
            norm_details["message"] = "No normalization needed"

        trace = self.create_trace("normalization", norm_status, norm_details, start)
        return norm_status, norm_details, trace