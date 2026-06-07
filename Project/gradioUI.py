import gradio as gr
from openai_client import chat_with_openai

def chat(message, history):
    yield from chat_with_openai(message, history)

def upload_pdf(file):
    return "File received: " + (file.name if file else "No file")

def create_ui():
    with gr.Blocks() as app:

        with gr.Row():
            with gr.Column():
                gr.ChatInterface(fn=chat,show_progress="minimal")

            with gr.Column():
                checklist = gr.Textbox(
                label="Checklist Status",
                value="Waiting for documents...")

        with gr.Row():
            upload = gr.File(label="Upload PDF")
            output = gr.Textbox(label="Upload Output")

            upload.change(
                fn=upload_pdf,
                inputs=upload,
                outputs=output
            )

    return app


if __name__ == "__main__":
    app = create_ui()
    app.launch()
