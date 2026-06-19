import os
import requests
import gradio as gr
from openai_client import chat_with_loan_classification, stream_chat_with_loan_classification
from loan_classifier import render_checklist, LOAN_REQUIREMENTS

FASTAPI_BASE = "http://127.0.0.1:8000"


def build_upload_feedback(filename, result, validation_state, loan_type_state):
    """
    Builds a chat-style feedback message after a file is validated.
    """
    lines = []
    matched = result.get("matched_document")
    partial_docs = [
        doc_result["document"]
        for doc_result in result.get("results", [])
        if doc_result.get("status") == "partial"
    ]

    if not result.get("readable", False):
        warning = result.get("warning", "PDF could not be read.")
        return f"📄 {filename}\n❓ {warning}"

    if matched:
        lines.append(f"📄 {filename} → matched {matched} ✅")
    elif partial_docs:
        if len(partial_docs) == 1:
            lines.append(f"📄 {filename} → partial match: {partial_docs[0]} ⚠️")
        else:
            lines.append(f"📄 {filename} → partial match: {', '.join(partial_docs)} ⚠️")
    else:
        lines.append(f"📄 {filename} → no document type matched ❌")

    # Figure out what's still missing — only "matched" counts as done
    if loan_type_state in LOAN_REQUIREMENTS:
        all_docs = [doc["name"] for doc in LOAN_REQUIREMENTS[loan_type_state]["required_documents"]]
        missing = [
            doc for doc in all_docs
            if validation_state.get(doc, "none") != "matched"
        ]
        if missing:
            lines.append(f"Still missing: {', '.join(missing)}")
        else:
            lines.append("🎉 All documents verified! Your application is complete.")

    return "\n".join(lines)


def chat_wrapper(message, history, loan_type_state, validation_state):
    # First show the user's message immediately, then continue with AI processing.
    history_with_user = history + [{"role": "user", "content": message}]
    checklist_text = render_checklist_from_state(loan_type_state, validation_state)
    yield history_with_user, checklist_text, loan_type_state, validation_state, None, None, None

    for partial_response, is_final, new_loan_type in stream_chat_with_loan_classification(
        message, history, loan_type_state
    ):
        if not is_final:
            yield (
                history_with_user + [{"role": "assistant", "content": partial_response}],
                checklist_text,
                loan_type_state,
                validation_state,
                None,
                None,
                None
            )
            continue

        upload_update = None
        upload_log_update = None
        output_update = None

        if new_loan_type != loan_type_state:
            validation_state = {}
            upload_update = gr.update(value=None)
            upload_log_update = []
            output_update = gr.update(value="")

        checklist_text = render_checklist_from_state(new_loan_type, validation_state)
        yield (
            history_with_user + [{"role": "assistant", "content": partial_response}],
            checklist_text,
            new_loan_type,
            validation_state,
            upload_update,
            upload_log_update,
            output_update
        )


def handle_upload(files, history, log, loan_type_state, validation_state):
    """
    Uploads and validates each file, updates checklist state,
    and injects feedback directly into the chat history.
    """
    if log is None:
        log = []

    if files is None:
        checklist_text = render_checklist_from_state(loan_type_state, validation_state)
        return history, log, "\n".join(log), checklist_text, validation_state

    if not isinstance(files, list):
        files = [files]

    # Track already-processed filenames to avoid re-uploading when
    # Gradio re-fires .change with all files on each new addition
    processed = {entry.split(": ")[-1] for entry in log if entry.startswith("📁 Uploaded:")}

    for file in files:
        filename = os.path.basename(file.name)

        if filename in processed:
            continue  # already handled in a previous .change event

        # --- Upload ---
        try:
            with open(file.name, "rb") as f:
                upload_resp = requests.post(
                    f"{FASTAPI_BASE}/upload",
                    files={"file": (filename, f, "application/pdf")}
                )
            if upload_resp.status_code != 200:
                log.append(f"❌ Upload failed for {filename}: {upload_resp.json().get('detail', 'Unknown error')}")
                continue
        except Exception as e:
            log.append(f"❌ Could not reach upload endpoint: {e}")
            continue

        log.append(f"📁 Uploaded: {filename}")

        # --- No loan type yet ---
        if loan_type_state == "none":
            log.append(f"⚠️  No loan type selected yet — skipping validation for {filename}")
            history = history + [{"role": "assistant", "content": f"📄 {filename} uploaded, but no loan type selected yet. Please tell me which loan you are applying for first."}]
            continue

        # --- Validate ---
        try:
            with open(file.name, "rb") as f:
                validate_resp = requests.post(
                    f"{FASTAPI_BASE}/validate",
                    files={"file": (filename, f, "application/pdf")},
                    data={"loan_type": loan_type_state}
                )
            if validate_resp.status_code != 200:
                log.append(f"❌ Validation failed for {filename}: {validate_resp.json().get('detail', 'Unknown error')}")
                continue
            result = validate_resp.json()
        except Exception as e:
            log.append(f"❌ Could not reach validate endpoint: {e}")
            continue

        # --- Update validation_state ---
        # Only record matched/partial — never write not_matched so that
        # documents not present in this file stay as "none" (still missing)
        priority = {"matched": 3, "partial": 2, "none": 0}
        for doc_result in result.get("results", []):
            doc_name = doc_result["document"]
            new_status = doc_result["status"]
            if new_status == "not_matched":
                continue
            existing = validation_state.get(doc_name, "none")
            if priority.get(new_status, 0) > priority.get(existing, 0):
                validation_state[doc_name] = new_status

        feedback = build_upload_feedback(filename, result, validation_state, loan_type_state)
        history = history + [{"role": "assistant", "content": feedback}]

    checklist_text = render_checklist_from_state(loan_type_state, validation_state)
    return history, log, "\n".join(log), checklist_text, validation_state


def render_checklist_from_state(loan_type, validation_state):
    """
    Renders checklist directly from LOAN_REQUIREMENTS dict — no HTTP call,
    so loan type switches always reflect instantly.
    """
    if loan_type == "none" or loan_type not in LOAN_REQUIREMENTS:
        return "Waiting for loan type selection..."

    loan_info = LOAN_REQUIREMENTS[loan_type]
    doc_names = [doc["name"] for doc in loan_info["required_documents"]]
    label = loan_info["label"]

    status_icon = {
        "matched":     "✅",
        "partial":     "⚠️",
        "not_matched": "❌",
        "none":        "⬜",
    }

    lines = [f"Checklist for {label}:", ""]
    for doc_name in doc_names:
        status = validation_state.get(doc_name, "none")
        icon = status_icon.get(status, "⬜")
        lines.append(f"{icon} {doc_name}")

    return "\n".join(lines)


def create_ui():
    with gr.Blocks() as app:
        gr.HTML("<h1 style='text-align:center;'>Loan Documentation Assistant</h1><hr>")

        loan_type_state = gr.State("none")
        validation_state = gr.State({})
        pending_msg = gr.State("")  # holds message while input is cleared

        checklist = gr.Textbox(
            label="Checklist",
            value="Waiting for loan type selection...",
            lines=10,
            render=False
        )

        with gr.Row():
            with gr.Column():
                gr.Markdown("### Chat with the AI Assistant")
                chatbot = gr.Chatbot(
                    value=[{"role": "assistant", "content": "Hello! I'm your AI assistant. How can I assist you?"}],
                    height=500,
                    autoscroll=True
                )
                msg_input = gr.Textbox(
                    placeholder="Type your message here...",
                    show_label=False,
                    submit_btn=True
                )

                submit_event = msg_input.submit(
                    fn=lambda msg: (msg, ""),
                    inputs=[msg_input],
                    outputs=[pending_msg, msg_input]
                )

            with gr.Column():
                gr.Markdown("### Document Checklist")
                checklist.render()

        gr.HTML("<hr><h3>Upload your PDF documents below. The AI will validate them against the checklist.</h3>")
        gr.Markdown("### Upload files Area")
        with gr.Row():
            upload = gr.File(label="Upload PDF", file_count="multiple")
            output = gr.Textbox(label="Upload Log", lines=8)
            upload_log = gr.State([])

            submit_event.then(
                fn=chat_wrapper,
                inputs=[pending_msg, chatbot, loan_type_state, validation_state],
                outputs=[chatbot, checklist, loan_type_state, validation_state, upload, upload_log, output],
                scroll_to_output=True,
                stream_every=0.1
            )

            upload.change(
                fn=handle_upload,
                inputs=[upload, chatbot, upload_log, loan_type_state, validation_state],
                outputs=[chatbot, upload_log, output, checklist, validation_state]
            )

    return app


if __name__ == "__main__":
    app = create_ui()
    app.launch()