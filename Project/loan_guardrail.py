import random

KEYWORDS = [
    "loan", "mortgage", "documents", "papers", "income",
    "bank statement", "employment", "pdf", "upload",
    "requirements", "application", "credit", "personal loan", "auto loan"
]

OFF_TOPIC_RESPONSES = [
    "Sorry, I can only help you with loan file requirements.",
    "How can I help you with your loan?",
    "I can only assist with loan documents and requirements.",
    "Let’s stay focused on your loan. What do you need help with?"
]

def is_loan_related(message: str) -> bool:
    msg = message.lower()
    return any(k in msg for k in KEYWORDS)

def guarded_chat(user_message, history, ai_callback):
    if not is_loan_related(user_message):
        # off-topic → single non-streaming response
        yield random.choice(OFF_TOPIC_RESPONSES)
        return

    for chunk in ai_callback(user_message, history):
        yield chunk
