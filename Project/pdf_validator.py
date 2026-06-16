import re
import json
import pdfplumber
from pathlib import Path

REQUIREMENTS_PATH = Path(__file__).parent / "loan_requirements.json"

with open(REQUIREMENTS_PATH, "r") as f:
    LOAN_REQUIREMENTS = json.load(f)

# Minimum number of characters extracted before we consider
# the PDF readable (image-based/scanned PDFs often return near nothing)
MIN_TEXT_LENGTH = 30

# Generic patterns used as layer 2 validation per document type
DOCUMENT_PATTERNS = {
    "Proof of Income": [
        r"\$[\d,]+(\.\d{2})?",        # currency amount e.g. $3,200.00
        r"\d{1,2}/\d{1,2}/\d{2,4}",   # date e.g. 01/15/2024
    ],
    "Bank Statement": [
        r"\$[\d,]+(\.\d{2})?",         # currency amount
        r"(debit|credit|deposit|withdrawal)",  # transaction keywords
    ],
    "Tax Return": [
        r"\$[\d,]+(\.\d{2})?",         # currency amount
        r"\b(19|20)\d{2}\b",           # 4-digit year
    ],
    "Government ID": [
        r"[A-Z0-9]{6,12}",             # alphanumeric ID number (6-12 chars)
    ],
    "Proof of Insurance": [
        r"[A-Z0-9]{6,12}",             # policy number
        r"\d{1,2}/\d{1,2}/\d{2,4}",   # coverage date
    ],
}

def extract_text(pdf_path: str) -> tuple[str, bool]:
    """
    Extracts all text from a PDF using pdfplumber.
    Returns (extracted_text, is_readable).
    is_readable is False if the PDF appears to be image-based / scanned.
    """
    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"

    is_readable = len(full_text.strip()) >= MIN_TEXT_LENGTH
    return full_text.lower(), is_readable


def validate_document(pdf_path: str, loan_type: str) -> dict:
    """
    Validates a PDF against the required documents for a given loan type.
    
    For each required document in the loan type's checklist, checks:
      - Layer 1: any keyword match in extracted text
      - Layer 2: any expected pattern match in extracted text
    
    Returns a dict with:
      - loan_type
      - filename
      - readable (bool)
      - results: list of per-document validation outcomes
      - matched_document: which document type this PDF most likely is
    """
    filename = Path(pdf_path).name

    if loan_type not in LOAN_REQUIREMENTS:
        return {
            "loan_type": loan_type,
            "filename": filename,
            "readable": False,
            "error": f"Unknown loan type: {loan_type}",
            "results": []
        }

    try:
        text, is_readable = extract_text(pdf_path)
    except Exception as e:
        return {
            "loan_type": loan_type,
            "filename": filename,
            "readable": False,
            "error": f"Could not read PDF: {str(e)}",
            "results": []
        }

    if not is_readable:
        return {
            "loan_type": loan_type,
            "filename": filename,
            "readable": False,
            "warning": "PDF appears to be image-based or scanned. Manual review recommended.",
            "results": []
        }

    # Validate each required document
    required_docs = LOAN_REQUIREMENTS[loan_type]["required_documents"]
    results = []
    matched_document = None

    for doc in required_docs:
        doc_name = doc["name"]
        keywords = doc["keywords"]
        patterns = DOCUMENT_PATTERNS.get(doc_name, [])

        # Layer 1: keyword match (OR logic — any keyword is enough)
        keyword_hit = any(kw in text for kw in keywords)

        # Layer 2: pattern match (OR logic — any pattern is enough)
        pattern_hit = any(re.search(p, text, re.IGNORECASE) for p in patterns) if patterns else False

        # Determine status
        if keyword_hit and pattern_hit:
            status = "matched"
            icon = "✅"
        elif keyword_hit or pattern_hit:
            status = "partial"
            icon = "⚠️"
        else:
            status = "not_matched"
            icon = "❌"

        if status == "matched" and matched_document is None:
            matched_document = doc_name

        results.append({
            "document": doc_name,
            "status": status,
            "icon": icon,
            "keyword_found": keyword_hit,
            "pattern_found": pattern_hit
        })

    return {
        "loan_type": loan_type,
        "filename": filename,
        "readable": True,
        "matched_document": matched_document,
        "results": results
    }