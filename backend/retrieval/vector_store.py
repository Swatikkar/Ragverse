from langchain_core.documents import Document
from typing import Any

import config
from config import CHROMA_DIR, TOP_K_RESULTS
from retrieval.embeded import get_embeddings
from utils.supabase_store import get_supabase, normalize_embedding, upsert_document_chunks
import os


_reranker = None
_user_stores: dict[str, Any] = {}


def _preserve_active_doc_coverage(ranked: list[Document], candidates: list[Document], doc_ids: list | None) -> list[Document]:
    if not doc_ids:
        return ranked

    selected_doc_ids = [str(doc_id) for doc_id in doc_ids]
    ranked_doc_ids = {str(doc.metadata.get("doc_id")) for doc in ranked}
    missing_doc_ids = [doc_id for doc_id in selected_doc_ids if doc_id not in ranked_doc_ids]
    if not missing_doc_ids:
        return ranked

    covered = []
    seen_chunks = set()
    for doc_id in missing_doc_ids:
        for doc in candidates:
            if str(doc.metadata.get("doc_id")) != doc_id:
                continue
            chunk_id = doc.metadata.get("chunk_id") or doc.page_content
            if chunk_id in seen_chunks:
                continue
            covered.append(doc)
            seen_chunks.add(chunk_id)
            break

    for doc in ranked:
        chunk_id = doc.metadata.get("chunk_id") or doc.page_content
        if chunk_id in seen_chunks:
            continue
        covered.append(doc)
        seen_chunks.add(chunk_id)

    return covered


def get_reranker():
    global _reranker
    if not config.ENABLE_RERANKER:
        return None
    if _reranker is None:
        try:
            from langchain_community.document_compressors.flashrank_rerank import FlashrankRerank
        except ImportError:
            return None

        _reranker = FlashrankRerank(top_n=6)
    return _reranker


def get_vector_store(user_id: str) -> Any:
    if user_id not in _user_stores:
        from langchain_chroma import Chroma

        user_chroma_dir = os.path.join(CHROMA_DIR, user_id)
        os.makedirs(user_chroma_dir, exist_ok=True)

        _user_stores[user_id] = Chroma(
            collection_name=f"ragverse_{user_id}",
            embedding_function=get_embeddings(),
            persist_directory=user_chroma_dir
        )
    return _user_stores[user_id]


def store_chunks(chunks: list[Document], user_id: str) -> int:
    if config.STORAGE_MODE == "supabase":
        if not chunks:
            return 0
        embeddings = get_embeddings().embed_documents([chunk.page_content for chunk in chunks])
        upsert_document_chunks(user_id, chunks, embeddings)
        return len(chunks)

    store = get_vector_store(user_id)
    store.add_documents(chunks)
    return len(chunks)


def _query_supabase_chunks(
    question: str,
    user_id: str,
    n_results: int,
    doc_ids: list | None = None,
    exclude_ids: set | None = None,
) -> list:
    client = get_supabase()
    if not client:
        return []

    exclude_ids = exclude_ids or set()
    query_embedding = normalize_embedding(get_embeddings().embed_query(question))

    def fetch_for_docs(ids: list | None, count: int) -> list[dict]:
        response = client.rpc(
            "match_document_chunks",
            {
                "match_user_id": user_id,
                "match_doc_ids": ids,
                "query_embedding": query_embedding,
                "match_count": count,
            },
        ).execute()
        return response.data or []

    if doc_ids:
        per_doc_k = max(2, min(4, n_results // max(1, len(doc_ids)) + 1))
        rows = []
        seen = set()
        for doc_id in doc_ids:
            for row in fetch_for_docs([doc_id], per_doc_k + len(exclude_ids)):
                chunk_id = row.get("chunk_id")
                if chunk_id and chunk_id not in seen:
                    seen.add(chunk_id)
                    rows.append(row)
    else:
        rows = fetch_for_docs(None, n_results + len(exclude_ids))

    candidates = []
    scores = {}
    for row in rows:
        chunk_id = row.get("chunk_id")
        if chunk_id in exclude_ids:
            continue
        metadata = row.get("metadata") or {}
        metadata["doc_id"] = metadata.get("doc_id") or row.get("doc_id")
        metadata["chunk_id"] = metadata.get("chunk_id") or chunk_id
        doc = Document(page_content=row.get("content") or "", metadata=metadata)
        candidates.append(doc)
        scores[chunk_id] = float(row.get("similarity") or 0)

    if not candidates:
        return []

    reranker = get_reranker()
    ranked = reranker.compress_documents(candidates, question) if reranker else candidates
    ranked = _preserve_active_doc_coverage(ranked, candidates, doc_ids)[:n_results]
    return [
        {
            "chunk": doc,
            "score": scores.get(doc.metadata.get("chunk_id"), 0.0),
            "from_cache": False,
        }
        for doc in ranked
    ]


def query_chunks(
    question: str,
    user_id: str,
    n_results: int = TOP_K_RESULTS,
    doc_ids: list | None = None,
    exclude_ids: set | None = None,
) -> list:
    if config.STORAGE_MODE == "supabase":
        return _query_supabase_chunks(question, user_id, n_results, doc_ids, exclude_ids)

    store = get_vector_store(user_id)
    exclude_ids = exclude_ids or set()

    def search_with_filter(filter_dict: dict | None, k: int) -> list[Document]:
        return store.max_marginal_relevance_search(
            query=question,
            k=k,
            fetch_k=max(20, k * 4),
            filter=filter_dict,
        )

    if doc_ids:
        per_doc_k = max(2, min(4, n_results // max(1, len(doc_ids)) + 1))
        docs = []
        seen_chunk_ids = set()
        for doc_id in doc_ids:
            for doc in search_with_filter({"doc_id": {"$eq": doc_id}}, per_doc_k + len(exclude_ids)):
                chunk_id = doc.metadata.get("chunk_id")
                if chunk_id and chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(chunk_id)
                    docs.append(doc)
    else:
        docs = search_with_filter(None, n_results + len(exclude_ids))

    filtered = [
        (doc, 0.5) for doc in docs
        if doc.metadata.get("chunk_id") not in exclude_ids
    ]
    if not filtered:
        return []

    candidates = [doc for doc, _score in filtered]
    scores = {doc.page_content: 0.5 for doc in candidates}
    reranker = get_reranker()
    reranked = reranker.compress_documents(candidates, question) if reranker else candidates
    reranked = _preserve_active_doc_coverage(reranked, candidates, doc_ids)[:n_results]

    return [
        {
            "chunk": doc,
            "score": scores.get(doc.page_content, 0.0),
            "from_cache": False,
        }
        for doc in reranked
    ]


def delete_document(doc_id: str, user_id: str):
    if config.STORAGE_MODE == "supabase":
        client = get_supabase()
        if client:
            client.table("document_chunks").delete().eq("user_id", user_id).eq("doc_id", doc_id).execute()
        return

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
                "source_url": metadata.get("source_url"),
            }

    return list(seen.values())
