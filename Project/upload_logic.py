# upload_logic.py
import os
import shutil

UPLOAD_DIR = "uploaded_pdfs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_uploaded_pdf(files, log):
    if files is None:
        return log, "\n".join(log)

    if not isinstance(files, list):
        files = [files]

    for file in files:
        temp_path = file.name
        filename = os.path.basename(temp_path)

        if not filename.lower().endswith(".pdf"):
            log.append(f"Error: {filename} is not a PDF file.")
            return log, "\n".join(log)

        save_path = os.path.join(UPLOAD_DIR, filename)
        shutil.copy(temp_path, save_path)

        log.append(f"Successfully uploaded {filename}!")

    return log, "\n".join(log)
