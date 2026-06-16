import json
from pathlib import Path
from openai_client import client, OPENAI_MODEL

REQUIREMENTS_PATH = Path(__file__).parent / "loan_requirements.json"

with open(REQUIREMENTS_PATH, "r") as f:
    LOAN_REQUIREMENTS = json.load(f)

VALID_LOAN_TYPES = list(LOAN_REQUIREMENTS.keys()) + ["none"]

CLASSIFIER_SYSTEM_PROMPT = f"""
You are a classifier for a loan documentation assistant.
Based on the conversation so far, determine which loan type the user is asking about.

Respond with EXACTLY ONE WORD, no punctuation, no explanation. Valid answers are:
{", ".join(LOAN_REQUIREMENTS.keys())}, none

Rules:
- "none" means the user has not indicated a specific loan type yet.
- If a loan type was already established earlier in the conversation and the user
  hasn't changed topic, respond with that same loan type again.
- If the user explicitly switches to a different loan type, respond with the new one.
"""

def classify_loan_type(message, history, current_loan_type="none"):
    messages = [{"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT}]

    for item in history:
        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content")
            if role and content:
                messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": message})
    messages.append({
        "role": "system",
        "content": f"Current loan type context: {current_loan_type}. Respond with one word only."
    })

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0,
        max_tokens=5
    )

    result = response.choices[0].message.content.strip().lower()

    if result not in VALID_LOAN_TYPES:
        return current_loan_type

    return result

def render_checklist(loan_type):
    if loan_type not in LOAN_REQUIREMENTS or loan_type == "none":
        return "Waiting for loan type selection..."

    loan_info = LOAN_REQUIREMENTS[loan_type]
    lines = [f"Checklist for {loan_info['label']}:", ""]

    for doc in loan_info["required_documents"]:
        lines.append(f"⬜ {doc['name']}")

    return "\n".join(lines)