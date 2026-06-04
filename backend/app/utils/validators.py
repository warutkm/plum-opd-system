import re
from typing import List

# Comprehensive patterns for Indian medical registration numbers.
# These match the patterns used in test_cases.json and the policy document.
_DOCTOR_REG_PATTERNS: List[re.Pattern] = [
    # Standard: KA/45678/2015, DL/34567/2016, TN/56789/2013
    re.compile(r"^[A-Z]{2}/\d{3,6}/\d{4}$"),
    # Ayurvedic: AYUR/KL/2345/2019
    re.compile(r"^AYUR/[A-Z]{2}/\d{3,6}/\d{4}$"),
    # Homeopathic: HOM/MH/1234/2020
    re.compile(r"^HOM/[A-Z]{2}/\d{3,6}/\d{4}$"),
    # Unani: UNANI/UP/5678/2018
    re.compile(r"^UNANI/[A-Z]{2}/\d{3,6}/\d{4}$"),
    # Siddha: SIDDHA/TN/7890/2017
    re.compile(r"^SIDDHA/[A-Z]{2}/\d{3,6}/\d{4}$"),
]


def validate_doctor_registration(reg_number: str) -> bool:
    """
    Validates Indian medical registration numbers.
    Supported formats:
      • KA/45678/2015          (Standard allopathic)
      • AYUR/KL/2345/2019      (Ayurvedic)
      • HOM/MH/1234/2020       (Homeopathic)
      • UNANI/UP/5678/2018     (Unani)
      • SIDDHA/TN/7890/2017    (Siddha)
    """
    cleaned = reg_number.strip().upper()
    return any(pat.match(cleaned) for pat in _DOCTOR_REG_PATTERNS)
