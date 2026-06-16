import os
from pathlib import Path

UPLOAD_DIR = str(Path(__file__).parent / "uploaded_pdfs")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_pdf_file(filename: str, content: bytes) -> str:
    if not filename.lower().endswith(".pdf"):
        raise ValueError(f"{filename} is not a PDF file.")

    save_path = os.path.join(UPLOAD_DIR, filename)
    with open(save_path, "wb") as f:
        f.write(content)

    return save_path

def save_uploaded_pdf(files, log):
    if files is None:
        return log, "\n".join(log)

    if not isinstance(files, list):
        files = [files]

    for file in files:
        filename = os.path.basename(file.name)
        try:
            with open(file.name, "rb") as f:
                content = f.read()
            save_pdf_file(filename, content)
            log.append(f"Successfully uploaded {filename}!")
        except ValueError as e:
            log.append(f"Error: {e}")

    return log, "\n".join(log)