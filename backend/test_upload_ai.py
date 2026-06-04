"""Quick test: 2-file upload to trigger AI extraction path."""

import io
import requests
import json
from PIL import Image, ImageDraw

BASE = "http://localhost:8001/api/v1/claims/upload"

def generate_png_image_with_text(text: str) -> bytes:
    # Create a blank white image
    img = Image.new("RGB", (800, 600), color="white")
    d = ImageDraw.Draw(img)
    # Draw the text line by line
    y = 20
    for line in text.split("\n"):
        d.text((20, y), line.strip(), fill="black")
        y += 25
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

rx_text = """
APOLLO HOSPITALS, BANGALORE
Patient Name: Rajesh Kumar
Age: 35 years
Date: 15/03/2025
Ref: Dr. Anita Sharma  Reg: KA/45678/2015

Diagnosis: Acute Pharyngitis

Rx:
- Paracetamol 650mg TDS x 3 days
- Vitamin C OD x 10 days

Advice: Warm saline gargles.
"""

bill_text = """
APOLLO HOSPITALS, BANGALORE
Bill No: INV-100293   Date: 15/03/2025
Patient Name: Rajesh Kumar

Ref: Dr. Anita Sharma  Reg: KA/45678/2015

Particulars               Amount (Rs.)
--------------------------------------
Consultation Fee          1,000.00
Diagnostic Tests (CBC)      500.00
--------------------------------------
TOTAL AMOUNT:             1,500.00
Payment Status: PAID
"""

rx_bytes = generate_png_image_with_text(rx_text)
bill_bytes = generate_png_image_with_text(bill_text)

files = [
    ("files", ("prescription.png", rx_bytes, "image/png")),
    ("files", ("bill.png", bill_bytes, "image/png")),
]

data = {
    "member_id": "EMP001",
    "treatment_date": "2025-03-15",
    "claim_amount": 1500.0,
    "hospital_name": "Apollo Hospitals",
}

print("Uploading to full AI extraction pipeline...")
resp = requests.post(BASE, files=files, data=data, timeout=120)
r = resp.json()
print(f"Status: {resp.status_code}")
print(f"Decision: {r.get('decision')}")
print(f"Amount: {r.get('approved_amount')}")
print(f"Confidence: {r.get('confidence_score')}")
print(f"Notes: {r.get('notes')}")
print()
for t in r.get("trace_summary", []):
    status = t["status"]
    icon = {"PASS": "OK", "WARNING": "WN", "FAIL": "FL", "SKIP": "SK"}.get(status, "??")
    print(f"  [{icon}] {t['step']}: {status} ({t.get('duration_ms',0)}ms)")
    if t["step"] == "ai_extraction" and t.get("details"):
        print(f"       confidence={t['details'].get('confidence')}")
        print(f"       diagnosis={t['details'].get('diagnosis')}")
        print(f"       provider={t['details'].get('provider')}")

