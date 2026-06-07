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

SYSTEM_PROMPT = """
You are a Loan File Documentation Assistant.
You help user figure out which loan they need and then you only assist them with required 
documentation for that loan. 

If the user asks something vague like "I need help with my loan":
You respond by asking specifically which loan type they are interested in.
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
