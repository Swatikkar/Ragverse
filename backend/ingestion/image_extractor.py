# backend/ingestion/image_extractor.py
import fitz
import os
import base64
import hashlib
from docx import Document
from pptx import Presentation
from config import MAX_IMAGES_PER_DOCUMENT, MIN_IMAGE_BYTES, UPLOAD_DIR


def extract_images(file_path: str, doc_id: str, user_id: str) -> list:
    ext = os.path.splitext(file_path)[-1].lower()

    # Scoped by user_id/doc_id
    image_dir = os.path.join(UPLOAD_DIR, user_id, doc_id, "images")
    os.makedirs(image_dir, exist_ok=True)

    if ext == ".pdf":
        return _extract_from_pdf(file_path, doc_id, image_dir)
    elif ext == ".docx":
        return _extract_from_docx(file_path, doc_id, image_dir)
    elif ext == ".pptx":
        return _extract_from_pptx(file_path, doc_id, image_dir)
    else:
        return []


def _save_image(image_bytes: bytes, image_path: str) -> str:
    with open(image_path, "wb") as f:
        f.write(image_bytes)
    return image_path


def _accept_image(image_bytes: bytes, seen_hashes: set[str], current_count: int) -> bool:
    if current_count >= MAX_IMAGES_PER_DOCUMENT or len(image_bytes) < MIN_IMAGE_BYTES:
        return False
    digest = hashlib.sha256(image_bytes).hexdigest()
    if digest in seen_hashes:
        return False
    seen_hashes.add(digest)
    return True


def _extract_from_pdf(file_path: str, doc_id: str, image_dir: str) -> list:
    doc = fitz.open(file_path)
    images = []
    seen_hashes = set()

    for page_num, page in enumerate(doc):
        for img_index, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            ext = base_image["ext"]
            if not _accept_image(image_bytes, seen_hashes, len(images)):
                continue

            image_filename = f"page{page_num + 1}_img{img_index}.{ext}"
            image_path = os.path.join(image_dir, image_filename)
            _save_image(image_bytes, image_path)

            images.append({
                "doc_id": doc_id,
                "doc_name": os.path.basename(file_path),
                "page_num": page_num + 1,
                "image_index": img_index,
                "image_path": image_path,
                "image_b64": base64.b64encode(image_bytes).decode("utf-8"),
                "source": "pdf"
            })

    doc.close()
    return images


def _extract_from_docx(file_path: str, doc_id: str, image_dir: str) -> list:
    doc = Document(file_path)
    images = []
    img_index = 0
    seen_hashes = set()

    for rel in doc.part.rels.values():
        if "image" in rel.reltype:
            image_bytes = rel.target_part.blob
            ext = rel.target_part.content_type.split("/")[-1]
            if not _accept_image(image_bytes, seen_hashes, len(images)):
                continue

            image_filename = f"section0_img{img_index}.{ext}"
            image_path = os.path.join(image_dir, image_filename)
            _save_image(image_bytes, image_path)

            images.append({
                "doc_id": doc_id,
                "doc_name": os.path.basename(file_path),
                "page_num": None,
                "section_index": 0,
                "image_index": img_index,
                "image_path": image_path,
                "image_b64": base64.b64encode(image_bytes).decode("utf-8"),
                "source": "docx"
            })
            img_index += 1

    return images


def _extract_from_pptx(file_path: str, doc_id: str, image_dir: str) -> list:
    prs = Presentation(file_path)
    images = []
    seen_hashes = set()

    for slide_index, slide in enumerate(prs.slides):
        img_index = 0
        for shape in slide.shapes:
            if shape.shape_type == 13:
                image_bytes = shape.image.blob
                ext = shape.image.ext
                if not _accept_image(image_bytes, seen_hashes, len(images)):
                    continue

                image_filename = f"slide{slide_index + 1}_img{img_index}.{ext}"
                image_path = os.path.join(image_dir, image_filename)
                _save_image(image_bytes, image_path)

                images.append({
                    "doc_id": doc_id,
                    "doc_name": os.path.basename(file_path),
                    "page_num": None,
                    "slide_index": slide_index + 1,
                    "image_index": img_index,
                    "image_path": image_path,
                    "image_b64": base64.b64encode(image_bytes).decode("utf-8"),
                    "source": "pptx"
                })
                img_index += 1

    return images
