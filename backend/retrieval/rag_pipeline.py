# backend/retrieval/rag_pipeline.py
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from retrieval.vector_store import query_chunks
from cache.cache_store import get_cached_chunks, add_to_cache
from config import LLM_MODEL

llm = ChatOllama(model=LLM_MODEL)

SYSTEM_PROMPT = """You are Ragverse, an intelligent AI assistant.

You are able to analyze any type of document activated — resumes, prescriptions, books, reports, contracts, spreadsheets, presentations etc. And you helps users to find the information they need from the documents and give answers to their queries using your own knowledge and the document analysis.

You have two sources of knowledge:
1. Document excerpts provided to you (when documents are active)
2. Your own general knowledge and training

Guidelines:
- Mostly refer to document if any of them is active,analyse it and response back to the queries using your trainings knowledge and the document analysis.
- When using document content, cite it as [Source N]
- When using your own knowledge, you don't need to cite anything
- If a question is about the document but the no relevant answer is there, just mention nothing related to the query is in the document but if the user wants you can help with your trained knowledge.
- Be helpful, conversational, and thorough
- Never say "I cannot answer this" if you can answer from your own knowledge"""

CHAT_SYSTEM_PROMPT = """You are Ragverse, a helpful and friendly AI assistant.
Answer questions naturally using your own knowledge.
Be conversational, helpful and thorough.
You also have the ability to analyze documents when the user activates them."""

def build_history(messages: list) -> str:
    if not messages:
        return ""
    history = []
    for msg in messages:
        role = "User" if msg["role"] == "user" else "Assistant"
        history.append(f"{role}: {msg['content']}")
    return "\n".join(history)

def build_context(chunks: list) -> str:
    context_blocks = []
    for i, item in enumerate(chunks):
        chunk = item["chunk"]
        meta = chunk.metadata

        source_label = f"[Source {i+1}: {meta.get('doc_name') or meta.get('source', 'Unknown')}, page {meta.get('page_num', 'N/A')}"
        if meta.get("type") == "image":
            source_label += ", image"
        source_label += "]"

        context_blocks.append(f"{source_label}\n{chunk.page_content}")

    return "\n\n---\n\n".join(context_blocks)

def chat(question: str, history: list = []) -> dict:
    """
    Normal chat mode — no documents active
    Uses only LLM knowledge
    """
    conversation = build_history(history)

    messages = [SystemMessage(content=CHAT_SYSTEM_PROMPT)]

    if conversation:
        messages.append(HumanMessage(
            content=f"Previous conversation:\n{conversation}\n\nContinue naturally."
        ))

    messages.append(HumanMessage(content=question))

    response = llm.invoke(messages)
    return {"answer": response.content, "sources": []}

def answer(question: str, doc_ids: list = None,
           session_id: str = None, history: list = []) -> dict:
    """
    RAG mode — documents are active
    Blends document knowledge + LLM knowledge
    """
    # Step 1 — Get cached chunks
    cached_chunks = []
    cached_ids = set()

    if session_id:
        cached_chunks = get_cached_chunks(session_id, doc_ids)
        cached_ids = {
            item["chunk"].metadata.get("chunk_id")
            for item in cached_chunks
        }

    # Step 2 — MMR search excluding cached chunks
    new_chunks = query_chunks(
        question,
        n_results=8,
        doc_ids=doc_ids,
        exclude_ids=cached_ids
    )

    # Step 3 — Add new chunks to cache
    if session_id and new_chunks:
        add_to_cache(session_id, new_chunks)

    # Step 4 — Merge + sort
    all_chunks = cached_chunks + new_chunks
    all_chunks = sorted(all_chunks, key=lambda x: x["score"], reverse=True)[:10]

    # Step 5 — Build messages
    conversation = build_history(history)
    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    if conversation:
        messages.append(HumanMessage(
            content=f"Previous conversation:\n{conversation}\n\nContinue naturally."
        ))

    # Step 6 — Add context if chunks found
    if all_chunks:
        context = build_context(all_chunks)
        messages.append(HumanMessage(content=f"""Here are relevant excerpts from the active documents:

{context}

Now answer this question using both the document excerpts AND your own knowledge where helpful:
{question}"""))
    else:
        # No relevant chunks found — fall back to own knowledge
        messages.append(HumanMessage(
            content=f"""No relevant document excerpts found for this question.
Answer using your own knowledge:
{question}"""
        ))

    response = llm.invoke(messages)

    # Step 7 — Build sources
    sources = []
    for item in all_chunks:
        meta = item["chunk"].metadata
        sources.append({
            "doc_id": meta.get("doc_id"),
            "doc_name": meta.get("doc_name") or meta.get("source"),
            "page_num": meta.get("page_num"),
            "type": meta.get("type", "text"),
            "image_path": meta.get("image_path"),
            "text_preview": item["chunk"].page_content[:150] + "...",
            "score": item["score"],
            "from_cache": item.get("from_cache", False)
        })

    return {"answer": response.content, "sources": sources}