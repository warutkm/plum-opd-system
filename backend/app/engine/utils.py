import re
from typing import Dict, List, Optional, Tuple, Set
from app.models.policy import PolicyTerms
from app.schemas.claim_schema import AdjudicationContext
from app.models.claim import ClaimCategory

_DOCTOR_REG_PATTERNS: List[re.Pattern] = [
    re.compile(r"^[A-Z]{2}/\d{3,6}/\d{4}$"),
    re.compile(r"^AYUR/[A-Z]{2}/\d{3,6}/\d{4}$"),
    re.compile(r"^HOM/[A-Z]{2}/\d{3,6}/\d{4}$"),
    re.compile(r"^UNANI/[A-Z]{2}/\d{3,6}/\d{4}$"),
    re.compile(r"^SIDDHA/[A-Z]{2}/\d{3,6}/\d{4}$"),
]

_EXCLUSION_KEYWORDS: Dict[str, List[str]] = {
    "Cosmetic procedures": [
        "cosmetic", "botox", "rhinoplasty", "liposuction",
        "hair transplant", "tummy tuck", "breast augmentation",
        "teeth whitening", "whitening", "veneers", "bleaching",
        "facelift", "dermabrasion",
    ],
    "Weight loss treatments": [
        "weight loss", "bariatric", "obesity", "slimming",
        "diet plan", "weight management", "weight reduction",
        "bmi", "gastric bypass", "gastric band",
    ],
    "Infertility treatments": [
        "infertility", "ivf", "fertility", "in vitro",
        "icsi", "iui", "surrogacy",
    ],
    "Experimental treatments": [
        "experimental", "clinical trial", "investigational",
        "unproven", "off-label",
    ],
    "Self-inflicted injuries": [
        "self-inflicted", "self harm", "self injury", "suicide attempt",
    ],
    "Adventure sports injuries": [
        "adventure sport", "bungee", "skydiving", "paragliding",
        "rock climbing", "scuba diving",
    ],
    "War and nuclear risks": ["war", "nuclear", "terrorism"],
    "HIV/AIDS treatment": ["hiv", "aids"],
    "Alcoholism/drug abuse treatment": [
        "alcoholism", "drug abuse", "substance abuse",
        "drug addiction", "alcohol addiction",
    ],
}

_BILL_KEY_CATEGORY: Dict[str, str] = {
    "consultation_fee": "consultation",
    "consultation": "consultation",
    "doctor_fee": "consultation",
    "diagnostic_tests": "diagnostic",
    "diagnostics": "diagnostic",
    "mri_scan": "diagnostic",
    "ct_scan": "diagnostic",
    "x_ray": "diagnostic",
    "blood_test": "diagnostic",
    "ultrasound": "diagnostic",
    "ecg": "diagnostic",
    "medicines": "pharmacy",
    "medicine": "pharmacy",
    "pharmacy": "pharmacy",
    "drugs": "pharmacy",
    "root_canal": "dental",
    "filling": "dental",
    "extraction": "dental",
    "cleaning": "dental",
    "dental": "dental",
    "teeth_whitening": "dental",
    "eye_test": "vision",
    "glasses": "vision",
    "contact_lenses": "vision",
    "therapy_charges": "alternative_medicine",
    "therapy": "alternative_medicine",
    "acupuncture": "alternative_medicine",
    "physiotherapy": "alternative_medicine",
}

_DENTAL_COSMETIC_KEYWORDS = [
    "whitening", "bleaching", "veneer", "implant",
    "braces", "orthodontic", "aligner", "invisalign",
    "cosmetic", "smile design",
]

# Generic bill keys that appear in any visit and should not independently
# determine whether a claim has covered items when the diagnosis is excluded.
_GENERIC_BILL_KEYS = {
    "consultation_fee", "consultation", "doctor_fee",
}

# Bill-item keys that represent excluded services.
_EXCLUDED_BILL_KEYS = {
    "diet_plan", "weight_loss", "slimming", "bariatric",
    "cosmetic", "teeth_whitening", "whitening", "bleaching",
    "ivf", "fertility", "hair_transplant",
    "botox", "liposuction", "tummy_tuck",
}

def get_copay_percentage(category: str, policy: PolicyTerms) -> float:
    if category in (ClaimCategory.CONSULTATION, ClaimCategory.MIXED):
        return policy.coverage_details.consultation_fees.copay_percentage
    return 0.0

def validate_doctor_registration(reg: str) -> bool:
    cleaned = reg.strip().upper()
    return any(pat.match(cleaned) for pat in _DOCTOR_REG_PATTERNS)

def is_network_hospital(hospital_name: Optional[str], policy: PolicyTerms) -> bool:
    if not hospital_name:
        return False
    name = hospital_name.lower().strip()
    return any(net.lower() in name or name in net.lower() for net in policy.network_hospitals)

def get_pre_auth_tests(policy: PolicyTerms) -> List[str]:
    tests: List[str] = []
    for t in policy.coverage_details.diagnostic_tests.covered_tests:
        if "(with pre-auth)" in t.lower():
            clean = re.sub(r"\(.*?\)", "", t).strip().lower()
            tests.append(clean)
    return tests

def requires_pre_auth(test_or_procedure: str, policy: PolicyTerms) -> bool:
    name = test_or_procedure.lower().strip()
    return any(pa in name for pa in get_pre_auth_tests(policy))

def is_excluded_diagnosis(diagnosis: str, procedures: List[str]) -> Tuple[bool, str]:
    combined = diagnosis + " " + " ".join(procedures)
    combined = combined.lower()
    for exclusion_name, keywords in _EXCLUSION_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return True, exclusion_name
    return False, ""

def is_excluded_procedure(procedure: str) -> bool:
    proc = procedure.lower()
    for keywords in _EXCLUSION_KEYWORDS.values():
        if any(kw in proc for kw in keywords):
            return True
    return False

def get_exclusion_reason(procedure: str) -> str:
    proc = procedure.lower()
    for exclusion_name, keywords in _EXCLUSION_KEYWORDS.items():
        if any(kw in proc for kw in keywords):
            return f"{exclusion_name} excluded from coverage"
    return "Excluded from coverage"

def is_cosmetic_dental(procedure: str, policy: PolicyTerms) -> bool:
    proc = procedure.lower().strip()
    for covered in policy.coverage_details.dental.procedures_covered:
        if covered.lower() in proc or proc in covered.lower():
            return False
    if any(kw in proc for kw in _DENTAL_COSMETIC_KEYWORDS):
        return True
    if not policy.coverage_details.dental.cosmetic_procedures:
        return any(kw in proc for kw in _DENTAL_COSMETIC_KEYWORDS)
    return False

def determine_category(ctx: AdjudicationContext) -> str:
    # 1. Check procedures for strong category signals (highest priority)
    for proc in (ctx.extracted_data.procedures or []):
        proc_lower = proc.lower()
        if any(kw in proc_lower for kw in [
            "panchakarma", "ayurved", "homeopath", "unani", "siddha", "acupuncture",
        ]):
            return ClaimCategory.ALTERNATIVE_MEDICINE.value
        if any(kw in proc_lower for kw in [
            "root canal", "filling", "extraction", "cleaning", "dental",
            "tooth", "crown", "bridge", "denture",
        ]):
            return ClaimCategory.DENTAL.value
        if any(kw in proc_lower for kw in [
            "lasik", "cataract", "eye test", "vision test",
        ]):
            return ClaimCategory.VISION.value

    # 2. Check doctor registration for alternative medicine prefix
    doc_reg = (ctx.extracted_data.doctor_registration or "").upper()
    if any(doc_reg.startswith(prefix) for prefix in ["AYUR/", "HOM/", "UNANI/", "SIDDHA/"]):
        return ClaimCategory.ALTERNATIVE_MEDICINE.value

    # 3. Bill-item-based categorization
    categories = set()
    for k in (ctx.bill_items or {}).keys():
        clean_k = k.lower().strip().replace(" ", "_").replace("-", "_")
        categories.add(_BILL_KEY_CATEGORY.get(clean_k, ClaimCategory.CONSULTATION.value))
    if len(categories) == 1:
        return list(categories)[0]
    elif len(categories) > 1:
        return ClaimCategory.MIXED.value

    # 4. Diagnosis-based fallback
    diag = (ctx.extracted_data.diagnosis or "").lower()
    if "dental" in diag or "tooth" in diag:
        return ClaimCategory.DENTAL.value
    if "eye" in diag or "vision" in diag:
        return ClaimCategory.VISION.value
    if "ayurveda" in diag or "therapy" in diag:
        return ClaimCategory.ALTERNATIVE_MEDICINE.value
    return ClaimCategory.CONSULTATION.value

def has_any_covered_items(procedures: List[str], bill_items: Dict[str, float], category: str, policy: PolicyTerms) -> bool:
    for proc in procedures:
        if not is_excluded_procedure(proc) and not is_cosmetic_dental(proc, policy):
            return True
    for key in bill_items:
        clean_key = key.lower().strip().replace(" ", "_").replace("-", "_")
        if clean_key in _GENERIC_BILL_KEYS:
            continue  # Generic fees don't independently prove coverage
        if clean_key in _EXCLUDED_BILL_KEYS:
            continue  # Known excluded service
        item_cat = _BILL_KEY_CATEGORY.get(clean_key, category)
        if item_cat != "excluded":
            return True
    return False

def match_procedures_to_amounts(procedures: List[str], bill_items: Dict[str, float]) -> Tuple[List[Tuple[str, float]], Set[str]]:
    result: List[Tuple[str, float]] = []
    used_keys: set = set()

    for proc in procedures:
        proc_norm = proc.lower().replace(" ", "_").replace("-", "_")
        amount = 0.0
        matched = False

        for key, val in bill_items.items():
            if key in used_keys:
                continue
            key_norm = key.lower()
            if key_norm == proc_norm:
                amount = val
                used_keys.add(key)
                matched = True
                break
            key_clean = key_norm.replace("_", " ")
            proc_clean = proc.lower()
            if key_clean in proc_clean or proc_clean in key_clean:
                amount = val
                used_keys.add(key)
                matched = True
                break
            key_parts = set(key_clean.split())
            proc_parts = set(proc_clean.split())
            if key_parts.intersection(proc_parts):
                amount = val
                used_keys.add(key)
                matched = True
                break

        if not matched:
            for key, val in bill_items.items():
                if key not in used_keys:
                    amount = val
                    used_keys.add(key)
                    break

        result.append((proc, amount))
    return result, used_keys
