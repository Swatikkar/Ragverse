import os
from fastapi import HTTPException
from config import AUDIO_EXTENSIONS
from ingestion.audio_loader import load_audio_transcript
from ingestion.document_loader import load_document
from ingestion.image_extractor import extract_images
from ingestion.image_describer import describe_image
from ingestion.chunker import chunk_documents, chunk_image_description


def process_document(file_path: str, doc_id: str, user_id: str) -> dict:

    ext = os.path.splitext(file_path)[-1].lower()

    try:
        if ext in AUDIO_EXTENSIONS:
            pages = load_audio_transcript(file_path, doc_id)
        else:
            pages = load_document(file_path, doc_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise ValueError(f"Could not process this source safely: {exc}") from exc

    text_chunks = chunk_documents(pages)

    image_chunks = []
    if ext in [".pdf", ".docx", ".pptx"]:
        images = extract_images(file_path, doc_id, user_id)

        for image in images:
            context = ""
            if image.get("page_num"):
                matching_pages = [
                    p.page_content for p in pages
                    if p.metadata.get("page_num") == image["page_num"]
                ]
                context = matching_pages[0][:300] if matching_pages else ""

            description = describe_image(
                image["image_b64"],
                context=context,
                page_num=image.get("page_num")
            )

            image_chunk = chunk_image_description(description, image)
            image_chunks.append(image_chunk)

    all_chunks = text_chunks + image_chunks

    return {
        "doc_id": doc_id,
        "user_id": user_id,
        "doc_name": os.path.basename(file_path),
        "text_chunks": len(text_chunks),
        "image_chunks": len(image_chunks),
        "total_chunks": len(all_chunks),
        "chunks": all_chunks
    }
