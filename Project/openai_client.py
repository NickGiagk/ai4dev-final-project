import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path.cwd().parent / ".env")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found. Set it in .env or your environment variables.")

from openai import OpenAI

client = OpenAI(api_key=OPENAI_API_KEY)

if client:
    print("OpenAI client initialized successfully.")

def chat_with_openai(message, history):
    messages = []

    if history:
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        max_tokens=500,
    )

    return response.choices[0].message.content

