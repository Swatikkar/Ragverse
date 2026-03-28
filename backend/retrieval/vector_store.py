# backend/retrieval/vector_store.py
from langchain_chroma import Chroma
from langchain_community.cross_encoders import FlashrankRerank
from retrieval.embeded import get_embeddings
from langchain_core.document_loaders import Document
from config import CHROMA_PATH, TOP_K_RESULTS

vector_store = Chroma(
    collection_name="documind",
    embedding_function=get_embeddings(),
    persist_directory=CHROMA_PATH
)

# Flashrank reranker
reranker = FlashrankRerank(top_n=6)

def store_chunks(chunks: list[Document]) -> int:
    vector_store.add_documents(chunks)
    return len(chunks)

def query_chunks(question: str, n_results: int = TOP_K_RESULTS,
                 doc_ids: list = None,
                 exclude_ids: set = None) -> list:

    filter_dict = None
    if doc_ids:
        filter_dict = {"doc_id": {"$in": doc_ids}}

    # MMR instead of similarity — balances relevance + diversity
    results = vector_store.max_marginal_relevance_search_with_score(
        query=question,
        k=n_results + len(exclude_ids or []),
        fetch_k=20,  # fetch more candidates, MMR picks best diverse subset
        filter=filter_dict
    )

    # Exclude cached chunks
    filtered = [
        (doc, score) for doc, score in results
        if score < 0.7
        and doc.metadata.get("chunk_id") not in (exclude_ids or set())
    ]

    if not filtered:
        return []

    # Rerank with Flashrank
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

def delete_document(doc_id: str):
    vector_store.delete(
        where={"doc_id": {"$eq": doc_id}}
    )