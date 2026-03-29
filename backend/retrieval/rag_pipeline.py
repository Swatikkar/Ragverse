# backend/retrieval/rag_pipeline.py
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from retrieval.vector_store import query_chunks
from cache.cache_store import get_cached_chunks, add_to_cache
from config import LLM_MODEL

llm = ChatOllama(model=LLM_MODEL)

SYSTEM_PROMPT = """You are DocuMind, an expert AI research assistant.
Answer questions using ONLY the provided document excerpts.
For every claim cite the source as [Source N].
If the answer is not in the documents say so clearly.
Be precise, thorough and research focused."""

def build_context(chunks: list) -> str:
    context_blocks = []
    for i, item in enumerate(chunks):
        chunk = item["chunk"]
        meta = chunk.metadata

        source_label = f"[Source {i+1}: {meta.get('doc_name', 'Unknown')}, page {meta.get('page_num', 'N/A')}"
        if meta.get("type") == "image":
            source_label += ", image"
        source_label += "]"

        context_blocks.append(f"{source_label}\n{chunk.page_content}")

    return "\n\n---\n\n".join(context_blocks)

def answer(question: str, doc_ids: list = None, session_id: str = None) -> dict:
    # Step 1 — Get cached chunks for this session
    cached_chunks = []
    cached_ids = set()

    if session_id:
        cached_chunks = get_cached_chunks(session_id, doc_ids)
        cached_ids = {
            item["chunk"].metadata.get("chunk_id")
            for item in cached_chunks
        }

    # Step 2 — MMR search excluding cached chunk ids
    new_chunks = query_chunks(
        question,
        n_results=8,
        doc_ids=doc_ids,
        exclude_ids=cached_ids
    )

    # Step 3 — Add new chunks to cache
    if session_id and new_chunks:
        add_to_cache(session_id, new_chunks)

    # Step 4 — Merge cached + new, sort by score, take top 10
    all_chunks = cached_chunks + new_chunks
    all_chunks = sorted(all_chunks, key=lambda x: x["score"], reverse=True)[:10]

    if not all_chunks:
        return {
            "answer": "No relevant content found in your documents.",
            "sources": []
        }

    # Step 5 — Build context
    context = build_context(all_chunks)

    # Step 6 — Call LLM
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"""DOCUMENT EXCERPTS:
{context}

QUESTION: {question}

Answer with citations:""")
    ]

    response = llm.invoke(messages)

    # Step 7 — Build sources for frontend
    sources = []
    for item in all_chunks:
        meta = item["chunk"].metadata
        sources.append({
            "doc_id": meta.get("doc_id", "unknown"),
            "doc_name": meta.get("doc_name", "unknown"),
            "page_num": meta.get("page_num"),
            "type": meta.get("type", "text"),
            "image_path": meta.get("image_path"),
            "text_preview": item["chunk"].page_content[:150] + "...",
            "score": item["score"],
            "from_cache": item.get("from_cache", False)
        })

    return {
        "answer": response.content,
        "sources": sources
    }