from __future__ import annotations

from langchain_core.documents import Document

import config
from cache.cache_store import add_to_cache, clear_doc_cache, clear_session_cache, get_cached_chunks
from ingestion.chunker import chunk_documents
from utils.supabase_store import normalize_embedding


def check_chunk_ids_are_document_wide() -> None:
    pages = [
        Document(page_content="Repeated opening text with one ending.", metadata={"doc_id": "doc-1"}),
        Document(page_content="Repeated opening text with another ending.", metadata={"doc_id": "doc-1"}),
    ]
    chunks = chunk_documents(pages)
    ids = [chunk.metadata["chunk_id"] for chunk in chunks]
    indexes = [chunk.metadata["chunk_index"] for chunk in chunks]
    assert len(ids) == len(set(ids))
    assert indexes == list(range(len(chunks)))


def check_cache_is_query_specific_and_invalidates() -> None:
    session_id = "optimization-session"
    user_id = "optimization-user"
    chunk = Document(page_content="cached result", metadata={"doc_id": "doc-1", "chunk_id": "chunk-1"})
    results = [{"chunk": chunk, "score": 0.9, "from_cache": False}]

    add_to_cache(session_id, "first question", ["doc-1"], results, user_id=user_id)
    assert get_cached_chunks(session_id, "first question", ["doc-1"], user_id=user_id)
    assert not get_cached_chunks(session_id, "different question", ["doc-1"], user_id=user_id)

    clear_doc_cache(session_id, "doc-1", user_id=user_id)
    assert not get_cached_chunks(session_id, "first question", ["doc-1"], user_id=user_id)
    clear_session_cache(session_id, user_id=user_id)


def check_embedding_dimension_validation() -> None:
    assert len(normalize_embedding([0.0] * config.EMBEDDING_DIMENSION)) == config.EMBEDDING_DIMENSION
    try:
        normalize_embedding([0.0])
    except ValueError:
        return
    raise AssertionError("Embedding dimension mismatch should fail instead of padding")


if __name__ == "__main__":
    check_chunk_ids_are_document_wide()
    check_cache_is_query_specific_and_invalidates()
    check_embedding_dimension_validation()
    print("All optimization checks passed.")
