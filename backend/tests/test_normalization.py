import sys
from datetime import date
from app.agents.normalization_agent import (
    _normalize_date,
    _normalize_doctor_registration,
    _normalize_amount,
    _normalize_provider,
)

def test_date_normalization():
    cases = [
        ("01/11/24", date(2024, 11, 1)),
        ("15/03/2025", date(2025, 3, 15)),
        ("2025-03-15", date(2025, 3, 15)),
        ("10.05.2025", date(2025, 5, 10)),
        ("20-04-2025", date(2025, 4, 20)),
        ("01/01/99", date(1999, 1, 1)),   # 99 → 1999
        ("", None),
        (None, None),
    ]
    for raw, expected in cases:
        assert _normalize_date(raw) == expected

def test_doctor_reg_normalization():
    cases = [
        ("ka-12345-2015", "KA/12345/2015"),
        ("KA/45678/2015", "KA/45678/2015"),
        ("ayur-kl-2345-2019", "AYUR/KL/2345/2019"),
        ("hom mh 1234 2020", "HOM/MH/1234/2020"),
        ("DL/34567/2016", "DL/34567/2016"),
        ("  ka/12345/2015  ", "KA/12345/2015"),
    ]
    for raw, expected in cases:
        assert _normalize_doctor_registration(raw) == expected

def test_amount_normalization():
    cases = [
        ("₹5,000", 5000.0),
        ("Rs. 1,500", 1500.0),
        ("Rs 8000", 8000.0),
        ("INR 2000", 2000.0),
        (1500.0, 1500.0),
        (8000, 8000.0),
        ("$100", 100.0),
        ("", None),
    ]
    for raw, expected in cases:
        assert _normalize_amount(raw) == expected

def test_provider_normalization():
    network = ["Apollo Hospitals", "Fortis Healthcare", "Max Healthcare", "Manipal Hospitals", "Narayana Health"]
    cases = [
        ("Apollo Hosp.", "Apollo Hospitals"),
        ("Apollo Hospitals", "Apollo Hospitals"),
        ("Fortis", "Fortis Healthcare"),
        ("Max Hosp", "Max Healthcare"),
        ("Narayana Health", "Narayana Health"),
        ("Some Random Clinic", "Some Random Clinic"),
    ]
    for raw, expected in cases:
        assert _normalize_provider(raw, network) == expected
