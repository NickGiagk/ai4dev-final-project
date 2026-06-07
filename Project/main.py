from fastapi import FastAPI
import gradio as gr
from gradioUI import create_ui

#############################
# FastAPI + Gradio          
#############################
app = FastAPI()

gradio_app = create_ui()
app = gr.mount_gradio_app(app, gradio_app, path="/ui")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)