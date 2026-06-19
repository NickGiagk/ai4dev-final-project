import json
from pathlib import Path

REQUIREMENTS_PATH = Path(__file__).parent / "loan_requirements.json"

with open(REQUIREMENTS_PATH, "r", encoding="utf-8") as f:
    LOAN_REQUIREMENTS = json.load(f)

VALID_LOAN_TYPES = list(LOAN_REQUIREMENTS.keys()) + ["none"]

CLASSIFIER_SYSTEM_PROMPT = f"""
You are a classifier for a loan documentation assistant.
Based on the conversation and especially the latest user message, determine which loan type the user is interested in.

Your response must begin with exactly one line in this format:
[LOAN_TYPE: <type>]

Where <type> is one of: {', '.join(VALID_LOAN_TYPES)}.

Rules:
- "none" means the user has not specified a loan type or is asking about loan documentation without changing the loan type.
- If the user clearly selects, switches, or asks about a different loan type, return the new loan type.
- If the user is only asking about documents, uploads, or validations and has not changed the loan type, return the current loan type.
- Do not add punctuation around the loan type marker.
"""

def render_checklist(loan_type):
    if loan_type not in LOAN_REQUIREMENTS or loan_type == "none":
        return "Waiting for loan type selection..."

    loan_info = LOAN_REQUIREMENTS[loan_type]
    lines = [f"Checklist for {loan_info['label']}:", ""]

    for doc in loan_info["required_documents"]:
        lines.append(f"⬜ {doc['name']}")

    return "\n".join(lines)