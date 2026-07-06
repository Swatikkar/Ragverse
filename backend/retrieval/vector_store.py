# backend/retrieval/vector_store.py
from langchain_chroma import Chroma
from langchain_community.document_compressors.flashrank_rerank import FlashrankRerank
from retrieval.embeded import get_embeddings
from langchain_core.documents import Document
from config import CHROMA_DIR, TOP_K_RESULTS
import os

# Flashrank reranker — shared across all users
reranker = FlashrankRerank(top_n=6)

# Per-user store cache — avoids recreating on every request
_user_stores: dict[str, Chroma] = {}


def get_vector_store(user_id: str) -> Chroma:
    if user_id not in _user_stores:
        # Each user gets their own subdirectory in chroma_db/
        user_chroma_dir = os.path.join(CHROMA_DIR, user_id)
        os.makedirs(user_chroma_dir, exist_ok=True)

        _user_stores[user_id] = Chroma(
            collection_name=f"ragverse_{user_id}",
            embedding_function=get_embeddings(),
            persist_directory=user_chroma_dir
        )
    return _user_stores[user_id]


def store_chunks(chunks: list[Document], user_id: str) -> int:
    store = get_vector_store(user_id)
    store.add_documents(chunks)
    return len(chunks)


def query_chunks(
    question: str,
    user_id: str,
    n_results: int = TOP_K_RESULTS,
    doc_ids: list = None,
    exclude_ids: set = None
) -> list:

    store = get_vector_store(user_id)

    filter_dict = None
    if doc_ids:
        filter_dict = {"doc_id": {"$in": doc_ids}}

    # MMR — balances relevance + diversity
    results = store.max_marginal_relevance_search(
        query=question,
        k=n_results + len(exclude_ids or []),
        fetch_k=20,
        filter=filter_dict
    )
    results = [(doc, 0.5) for doc in results]

    # Exclude cached chunks
    filtered = [
        (doc, score) for doc, score in results
        if score < 0.7
        and doc.metadata.get("chunk_id") not in (exclude_ids or set())
    ]

    if not filtered:
        return []

    docs = [doc for doc, _ in filtered]
    scores = {doc.page_content: round(1 - score, 3) for doc, score in filtered}

    reranked = reranker.compress_documents(docs, question)

    return [
        {
            "chunk": doc,
            "score": scores.get(doc.page_content, 0.0),
            "from_cache": False
        }
        for doc in reranked
    ]


def delete_document(doc_id: str, user_id: str):
    store = get_vector_store(user_id)
    store.delete(where={"doc_id": {"$eq": doc_id}})


def get_all_documents(user_id: str) -> list:
    store = get_vector_store(user_id)
    results = store.get()
    seen = {}

    for metadata in results["metadatas"]:
        doc_id = metadata.get("doc_id")
        if doc_id and doc_id not in seen:
            seen[doc_id] = {
                "doc_id": doc_id,
                "doc_name": metadata.get("doc_name") or metadata.get("source"),
                "file_type": metadata.get("file_type"),
                "source_type": metadata.get("source_type", "document"),
                "source_url": metadata.get("source_url")
            }

    return list(seen.values())
