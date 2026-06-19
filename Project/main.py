import json
import os
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
import gradio as gr

from gradioUI import create_ui
from upload_logic import save_pdf_file, UPLOAD_DIR
from pdf_validator import validate_document

REQUIREMENTS_PATH = Path(__file__).parent / "loan_requirements.json"

with open(REQUIREMENTS_PATH, "r") as f:
    LOAN_REQUIREMENTS = json.load(f)

#############################
# FastAPI                   #
#############################
app = FastAPI(title="Loan Documentation Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Accepts a PDF file upload, saves it to disk.
    Returns the saved filename on success.
    """
    content = await file.read()
    try:
        saved_path = save_pdf_file(file.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "success",
        "filename": file.filename,
        "path": saved_path
    }


@app.get("/checklist/{loan_type}")
def get_checklist(loan_type: str):
    """
    Returns the required documents for a given loan type as JSON.
    Example: GET /checklist/mortgage
    """
    if loan_type not in LOAN_REQUIREMENTS:
        raise HTTPException(
            status_code=404,
            detail=f"Loan type '{loan_type}' not found. Valid types: {list(LOAN_REQUIREMENTS.keys())}"
        )

    loan_info = LOAN_REQUIREMENTS[loan_type]
    return {
        "loan_type": loan_type,
        "label": loan_info["label"],
        "required_documents": [doc["name"] for doc in loan_info["required_documents"]]
    }


@app.post("/validate")
async def validate_pdf(
    file: UploadFile = File(...),
    loan_type: str = Form(...)
):
    """
    Accepts a PDF and a loan_type, runs pdfplumber extraction + validation,
    and returns per-document validation results.

    Example form fields:
      - file: <pdf file>
      - loan_type: mortgage | personal_loan | auto_loan
    """
    if loan_type not in LOAN_REQUIREMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown loan type '{loan_type}'. Valid types: {list(LOAN_REQUIREMENTS.keys())}"
        )

    # Save the file temporarily so pdfplumber can open it from disk
    content = await file.read()
    try:
        saved_path = save_pdf_file(file.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Run validation
    result = validate_document(saved_path, loan_type)

    return result


#############################
# Gradio                    #
#############################
gradio_app = create_ui()
app = gr.mount_gradio_app(app, gradio_app, path="/ui")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000)