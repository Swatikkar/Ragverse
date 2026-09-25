# backend/ingestion/chunker.py
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from config import CHUNK_SIZE, CHUNK_OVERLAP
import hashlib

splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " "]
)


def _make_chunk_id(doc_id: str, content: str, index: int) -> str:
    """Stable unique id based on doc_id + content + index"""
    raw = f"{doc_id}\0{index}\0{content}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def chunk_documents(pages: list) -> list:
    chunks = []
    global_index = 0

    for page in pages:
        splits = splitter.split_documents([page])
        for split in splits:
            split.metadata["chunk_index"] = global_index
            split.metadata["type"] = split.metadata.get("type", "text")
            split.metadata["source_type"] = split.metadata.get("source_type", "document")
            split.metadata["chunk_id"] = _make_chunk_id(
                split.metadata.get("doc_id", ""),
                split.page_content,
                global_index
            )
            chunks.append(split)
            global_index += 1

    return chunks


def chunk_image_description(description: str, image_metadata: dict) -> Document:
    doc_id = image_metadata["doc_id"]
    image_index = image_metadata["image_index"]

    return Document(
        page_content=description,
        metadata={
            "doc_id": doc_id,
            "doc_name": image_metadata["doc_name"],
            "page_num": image_metadata.get("page_num"),
            "slide_index": image_metadata.get("slide_index"),
            "section_index": image_metadata.get("section_index"),
            "image_index": image_index,
            "image_path": image_metadata["image_path"],
            "chunk_index": 0,
            "type": "image",
            "chunk_id": _make_chunk_id(doc_id, description, image_index)
        }
    )
