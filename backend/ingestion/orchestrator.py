# import uuid
import os
from ingestion.document_loader import load_document
from ingestion.image_extractor import extract_images
from ingestion.image_describer import describe_image
from ingestion.chunker import chunk_documents, chunk_image_description
from config import UPLOAD_DIR

def process_document(file_path: str,doc_id: str) -> dict:

    # Create doc directory in uploads
    doc_dir = os.path.join(UPLOAD_DIR, doc_id)
    os.makedirs(doc_dir, exist_ok=True)

    ext = os.path.splitext(file_path)[-1].lower()

    # Step 1 — Load text via LangChain
    pages = load_document(file_path, doc_id)

    # Step 2 — Chunk text pages
    text_chunks = chunk_documents(pages)

    # Step 3 — Extract images (PDF, DOCX, PPTX only)
    image_chunks = []
    if ext in [".pdf", ".docx", ".pptx"]:
        images = extract_images(file_path, doc_id)

        for image in images:
            # Get context text from same page
            context = ""
            if image.get("page_num"):
                matching_pages = [
                    p.page_content for p in pages
                    if p.metadata.get("page_num") == image["page_num"]
                ]
                context = matching_pages[0][:300] if matching_pages else ""

            # Step 4 — Describe image with context
            description = describe_image(
                image["image_b64"],
                context=context,
                page_num=image.get("page_num")
            )

            # Step 5 — Chunk image description
            image_chunk = chunk_image_description(description, image)
            image_chunks.append(image_chunk)

    # Step 6 — Combine all chunks
    all_chunks = text_chunks + image_chunks

    return {
        "doc_id": doc_id,
        "doc_name": os.path.basename(file_path),
        "text_chunks": len(text_chunks),
        "image_chunks": len(image_chunks),
        "total_chunks": len(all_chunks),
        "chunks": all_chunks  # passed to vector_store next
    }