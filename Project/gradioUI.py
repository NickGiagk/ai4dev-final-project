import gradio as gr
from openai_client import chat_with_openai
from upload_logic import save_uploaded_pdf
from loan_guardrail import guarded_chat
from loan_classifier import classify_loan_type, render_checklist

def chat_wrapper(message, history, loan_type_state):
    new_loan_type = classify_loan_type(message, history, loan_type_state)
    checklist_text = render_checklist(new_loan_type)

    for chunk in guarded_chat(message, history, chat_with_openai):
        yield chunk, checklist_text, new_loan_type

def upload_pdf(file):
    return "File received: " + (file.name if file else "No file")

def create_ui():
    with gr.Blocks() as app:
        loan_type_state = gr.State("none")

        checklist = gr.Textbox(
            label="Checklist",
            value="Waiting for loan type selection...",
            lines=10,
            render=False
        )

        with gr.Row():
            with gr.Column():
                gr.ChatInterface(
                    fn=chat_wrapper,
                    show_progress="minimal",
                    chatbot=gr.Chatbot(value=[
                        {
                            "role": "assistant",
                            "content": "Hello! I'm your AI assistant. How can I assist you?"
                        }
                    ]),
                    additional_inputs=[loan_type_state],
                    additional_outputs=[checklist, loan_type_state],
                )

            with gr.Column():
                checklist.render()

        with gr.Row():
            upload = gr.File(label="Upload PDF", file_count="multiple")
            output = gr.Textbox(label="Upload Log", lines=5)
            upload_log = gr.State([])

            upload.change(
                fn=save_uploaded_pdf,
                inputs=[upload, upload_log],
                outputs=[upload_log, output]
            )
    return app

if __name__ == "__main__":
    app = create_ui()
    app.launch()