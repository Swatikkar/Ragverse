# backend/utils/file_handler.py
import os
import shutil
from fastapi import UploadFile, HTTPException
from config import UPLOAD_DIR, MAX_FILE_SIZE_BYTES, ALLOWED_EXTENSIONS

def validate_file(file: UploadFile) -> str:
    """
    Validates file type and size
    Returns file extension
    """
    ext = os.path.splitext(file.filename)[-1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {ALLOWED_EXTENSIONS}"
        )

    return ext

async def save_upload(file: UploadFile, doc_id: str) -> str:
    """
    Saves uploaded file to uploads/{doc_id}/filename
    Returns full file path
    """
    # Validate first
    validate_file(file)

    # Create doc directory
    doc_dir = os.path.join(UPLOAD_DIR, doc_id)
    os.makedirs(doc_dir, exist_ok=True)

    file_path = os.path.join(doc_dir, file.filename)

    # Read and check size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB"
        )

    # Save to disk
    with open(file_path, "wb") as f:
        f.write(contents)

    return file_path

def delete_upload(doc_id: str):
    """
    Deletes entire doc directory including images
    Called when user removes a document
    """
    doc_dir = os.path.join(UPLOAD_DIR, doc_id)
    if os.path.exists(doc_dir):
        shutil.rmtree(doc_dir)