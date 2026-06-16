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
You are a Loan File Documentation Assistant.

RULES:
1. Answer ONLY using information contained in the JSON below.
2. If the information is not in the JSON, reply exactly:
   "Sorry, I can only help you with loan file requirements."
3. Do not invent requirements.
4. Do not answer general knowledge questions.
5. If the user has not specified a loan type, ask them which loan type they need.

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
