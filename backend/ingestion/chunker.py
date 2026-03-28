# backend/ingestion/chunker.py
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from config import CHUNK_SIZE, CHUNK_OVERLAP

splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " "]
)

def chunk_documents(pages: list) -> list:
    """
    Takes LangChain Document pages from document_loader
    Returns list of smaller chunks with preserved metadata
    """
    chunks = []

    for page in pages:
        splits = splitter.split_documents([page])
        for i, split in enumerate(splits):
            # Preserve all existing metadata from document_loader
            split.metadata["chunk_index"] = i
            split.metadata["type"] = "text"
            chunks.append(split)

    return chunks

def chunk_image_description(description: str, image_metadata: dict) -> Document:
    """
    Wraps image description into a LangChain Document
    with full image metadata for linking back
    """
    return Document(
        page_content=description,
        metadata={
            "doc_id": image_metadata["doc_id"],
            "doc_name": image_metadata["doc_name"],
            "page_num": image_metadata.get("page_num"),
            "slide_index": image_metadata.get("slide_index"),
            "section_index": image_metadata.get("section_index"),
            "image_index": image_metadata["image_index"],
            "image_path": image_metadata["image_path"],
            "chunk_index": 0,
            "type": "image"
        }
    )