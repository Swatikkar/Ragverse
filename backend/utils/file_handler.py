import os
import shutil
import magic
from fastapi import UploadFile, HTTPException
from config import UPLOAD_DIR, MAX_FILE_SIZE_BYTES, ALLOWED_EXTENSIONS

# Allowed MIME types mapped to extensions
ALLOWED_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/plain",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation"
}

def validate_file(file: UploadFile, contents: bytes) -> str:
    # Check extension
    ext = os.path.splitext(file.filename)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {ALLOWED_EXTENSIONS}"
        )

    # Check file size
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB"
        )

    # Check magic bytes — actual file content
    mime = magic.from_buffer(contents, mime=True)
    allowed_mime = ALLOWED_MIME_TYPES.get(ext)

    # CSV is flexible — can be text/plain or text/csv
    if ext == ".csv" and mime in ["text/plain", "text/csv"]:
        return ext

    if mime != allowed_mime:
        raise HTTPException(
            status_code=400,
            detail=f"File content does not match extension. Expected {allowed_mime}, got {mime}"
        )

    # Check file is not empty
    if len(contents) == 0:
        raise HTTPException(
            status_code=400,
            detail="File is empty"
        )

    return ext

async def save_upload(file: UploadFile, doc_id: str) -> str:
    # Read contents first
    contents = await file.read()

    # Validate
    validate_file(file, contents)

    # Create doc directory
    doc_dir = os.path.join(UPLOAD_DIR, doc_id)
    os.makedirs(doc_dir, exist_ok=True)

    file_path = os.path.join(doc_dir, file.filename)

    # Save to disk
    with open(file_path, "wb") as f:
        f.write(contents)

    return file_path

def delete_upload(doc_id: str):
    doc_dir = os.path.join(UPLOAD_DIR, doc_id)
    if os.path.exists(doc_dir):
        shutil.rmtree(doc_dir)