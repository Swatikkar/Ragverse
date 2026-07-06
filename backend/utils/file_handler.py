# backend/utils/file_handler.py
import os
import shutil
import filetype
from fastapi import UploadFile, HTTPException
from config import AUDIO_EXTENSIONS, MAX_AUDIO_SIZE_BYTES, MAX_FILE_SIZE_BYTES, UPLOAD_DIR, ALLOWED_EXTENSIONS
from utils.security import sanitize_name

ALLOWED_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/plain",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".mp3": "audio/mpeg",
    ".wav": "audio/x-wav",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".webm": "video/webm",
    ".mp4": "video/mp4",
}


def _looks_like_text(contents: bytes) -> bool:
    try:
        contents.decode("utf-8")
        return True
    except UnicodeDecodeError:
        try:
            contents.decode("utf-8-sig")
            return True
        except UnicodeDecodeError:
            return False


def _detect_mime(contents: bytes, ext: str) -> str | None:
    if ext == ".csv" and _looks_like_text(contents):
        return "text/csv"
    kind = filetype.guess(contents)
    return kind.mime if kind else None


def validate_file(file: UploadFile, contents: bytes) -> str:
    ext = os.path.splitext(file.filename)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {ALLOWED_EXTENSIONS}"
        )

    max_bytes = MAX_AUDIO_SIZE_BYTES if ext in AUDIO_EXTENSIONS else MAX_FILE_SIZE_BYTES
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size is {max_bytes // (1024 * 1024)}MB"
        )

    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    mime = _detect_mime(contents, ext)
    allowed_mime = ALLOWED_MIME_TYPES.get(ext)

    if ext == ".csv" and mime in ["text/plain", "text/csv"]:
        return ext

    if ext in AUDIO_EXTENSIONS and mime and mime.startswith(("audio/", "video/")):
        return ext

    if mime != allowed_mime:
        raise HTTPException(
            status_code=400,
            detail=f"File content does not match extension. Expected {allowed_mime}, got {mime or 'unknown'}"
        )

    return ext


async def save_upload(file: UploadFile, doc_id: str, user_id: str) -> str:
    contents = await file.read()
    validate_file(file, contents)

    # Scoped by user_id/doc_id
    doc_dir = os.path.join(UPLOAD_DIR, user_id, doc_id)
    os.makedirs(doc_dir, exist_ok=True)

    ext = os.path.splitext(file.filename)[-1].lower()
    safe_filename = sanitize_name(file.filename, fallback=f"{doc_id}{ext}")
    file_path = os.path.join(doc_dir, safe_filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    return file_path


def delete_upload(doc_id: str, user_id: str):
    doc_dir = os.path.join(UPLOAD_DIR, user_id, doc_id)
    if os.path.exists(doc_dir):
        shutil.rmtree(doc_dir)
