import gradio as gr
from openai_client import chat_with_openai
from upload_logic import save_uploaded_pdf
from loan_guardrail import guarded_chat

def chat_wrapper(message, history):
    yield from guarded_chat(message, history, chat_with_openai)

def upload_pdf(file):
    return "File received: " + (file.name if file else "No file")

def create_ui():
    with gr.Blocks() as app:

        with gr.Row():
            with gr.Column():
                gr.ChatInterface(
                    fn=chat_wrapper,
                    show_progress="minimal"
                )

            with gr.Column():
                checklist = gr.Textbox(
                    label="Checklist",
                    value="Waiting User selection..."
                )

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
