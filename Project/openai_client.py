import os
import re
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from loan_classifier import CLASSIFIER_SYSTEM_PROMPT, VALID_LOAN_TYPES

load_dotenv(Path.cwd().parent / ".env")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found. Set it in .env or your environment variables.")

client = OpenAI(api_key=OPENAI_API_KEY)

if client:
    print("OpenAI client initialized successfully.")

REQUIREMENTS_PATH = Path(__file__).parent / "loan_requirements.json"

with open(REQUIREMENTS_PATH, "r", encoding="utf-8") as file:
    requirements_data = file.read()

UNIFIED_SYSTEM_PROMPT = f"""
{CLASSIFIER_SYSTEM_PROMPT}

You are also the loan document assistant.
Answer the user's question using the loan requirements JSON below.
If the user asks about a specific document or validation step, explain what documents are required and what is missing.
If the user asks about the current loan, or if the prompt is about changing loans,
return the loan type in the [LOAN_TYPE: <type>] marker at the top.

LOAN REQUIREMENTS JSON:
{requirements_data}
"""


def extract_loan_type_from_response(response, current_loan_type="none"):
    match = re.search(r'^\[LOAN_TYPE:\s*([^\]]+)\]', response, re.IGNORECASE)
    if not match:
        return current_loan_type

    extracted = match.group(1).strip().lower()
    normalized = extracted.replace(" ", "_")
    if normalized in VALID_LOAN_TYPES:
        return normalized
    if extracted in VALID_LOAN_TYPES:
        return extracted
    return current_loan_type


def _build_chat_messages(message, history, current_loan_type="none"):
    messages = [{"role": "system", "content": UNIFIED_SYSTEM_PROMPT}]
    messages.append({"role": "system", "content": f"Current loan type context: {current_loan_type}."})

    for item in history:
        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content")
            if role and content:
                messages.append({"role": role, "content": content})
        elif isinstance(item, tuple):
            if len(item) >= 1 and item[0]:
                messages.append({"role": "user", "content": item[0]})
            if len(item) >= 2 and item[1]:
                messages.append({"role": "assistant", "content": item[1]})

    messages.append({"role": "user", "content": message})
    return messages


def chat_with_loan_classification(message, history, current_loan_type="none"):
    messages = _build_chat_messages(message, history, current_loan_type)

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.7
    )

    full_response = response.choices[0].message.content
    loan_type = extract_loan_type_from_response(full_response, current_loan_type)
    clean_response = re.sub(r'^\[LOAN_TYPE:\s*[^\]]+\]\s*', '', full_response, flags=re.IGNORECASE).strip()

    return loan_type, clean_response


def stream_chat_with_loan_classification(message, history, current_loan_type="none"):
    messages = _build_chat_messages(message, history, current_loan_type)

    stream = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.7,
        stream=True
    )

    accumulated = ""
    for chunk in stream:
        delta = getattr(chunk.choices[0], "delta", None)
        content = ""
        if delta is not None:
            content = getattr(delta, "content", "")
        if content:
            accumulated += content
            yield accumulated, False, None

    loan_type = extract_loan_type_from_response(accumulated, current_loan_type)
    clean_response = re.sub(r'^\[LOAN_TYPE:\s*[^\]]+\]\s*', '', accumulated, flags=re.IGNORECASE).strip()
    yield clean_response, True, loan_type