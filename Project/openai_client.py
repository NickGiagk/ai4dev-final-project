import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

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

SYSTEM_PROMPT = f"""
You are a friendly Loan File Documentation Assistant.
Your job is to help users understand which documents they need for their loan application.

RULES:
1. Be conversational and helpful. You may greet the user, ask clarifying questions,
   and guide them naturally through the process.
2. When listing required documents for a loan, use ONLY the documents defined in the
   LOAN REQUIREMENTS JSON below. Do not invent or add extra requirements.
3. If the user has not specified a loan type yet, ask them which one they are interested in.
4. If the user asks something completely unrelated to loans or documents
   (e.g. weather, sports, coding), politely decline and redirect to loan topics.
5. Keep answers concise and friendly.

LOAN REQUIREMENTS JSON:
{requirements_data}
"""


def chat_with_openai(message, history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

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

    partial = ""
    for chunk in client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        stream=True
    ):
        delta = chunk.choices[0].delta
        if delta and delta.content:
            partial += delta.content
            yield partial