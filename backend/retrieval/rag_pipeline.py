# backend/retrieval/rag_pipeline.py
from langchain_core.messages import HumanMessage, SystemMessage
from retrieval.vector_store import query_chunks
from cache.cache_store import get_cached_chunks, add_to_cache
from providers import model_router
from starlette.concurrency import run_in_threadpool
import config

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
No documents are currently active. If the user asks about an uploaded file,
document, audio file, URL, spreadsheet, presentation, or source-specific fact,
politely explain that no document is active to discuss and ask them to activate
the relevant item first."""


def build_history(messages: list, include_assistant: bool = True, limit: int = 8) -> str:
    if not messages:
        return ""
    history = []
    for msg in messages[-limit:]:
        if not include_assistant and msg.get("role") != "user":
            continue
        role = "User" if msg["role"] == "user" else "Assistant"
        content = (msg.get("content") or "").strip()
        if content:
            history.append(f"{role}: {content}")
    return "\n".join(history)


def build_context(chunks: list) -> str:
    context_blocks = []
    for i, item in enumerate(chunks):
        chunk = item["chunk"]
        meta = chunk.metadata

        source_label = f"[Source {i+1}: {meta.get('doc_name') or meta.get('source', 'Unknown')}, page {meta.get('page_num', 'N/A')}"
        if meta.get("source_type") == "url":
            source_label = f"[Source {i+1}: {meta.get('doc_name') or 'URL'}, {meta.get('source_url')}]"
        elif meta.get("source_type") == "audio":
            source_label = f"[Source {i+1}: {meta.get('doc_name') or 'Audio transcript'}]"
        if meta.get("type") == "image":
            source_label += ", image"
        source_label += "]"

        context_blocks.append(f"{source_label}\n{chunk.page_content}")

    return "\n\n---\n\n".join(context_blocks)


def chat(question: str, history: list | None = None) -> dict:
    conversation = build_history(history)
    messages = [SystemMessage(content=CHAT_SYSTEM_PROMPT)]

    if conversation:
        messages.append(HumanMessage(
            content=f"Previous conversation:\n{conversation}\n\nContinue naturally."
        ))
    messages.append(HumanMessage(content=question))
    response, _metadata = model_router.invoke_chat("rag_chat", messages)
    return {"answer": response.content, "sources": []}


def _retrieve_chunks(question: str, doc_ids: list | None, session_id: str | None, user_id: str | None) -> list:
    if session_id and config.STORAGE_MODE != "supabase":
        cached_chunks = get_cached_chunks(session_id, question, doc_ids, user_id=user_id)
        if cached_chunks:
            return cached_chunks

    chunks = query_chunks(
        question,
        user_id=user_id,
        n_results=config.TOP_K_RESULTS,
        doc_ids=doc_ids,
    )
    if session_id and chunks and config.STORAGE_MODE != "supabase":
        add_to_cache(session_id, question, doc_ids, chunks, user_id=user_id)
    return chunks[:10]


def _build_sources(chunks: list) -> list[dict]:
    sources = []
    for item in chunks:
        meta = item["chunk"].metadata
        sources.append({
            "doc_id": meta.get("doc_id"),
            "chunk_id": meta.get("chunk_id"),
            "doc_name": meta.get("doc_name") or meta.get("source"),
            "page_num": meta.get("page_num"),
            "type": meta.get("type", "text"),
            "source_type": meta.get("source_type", "document"),
            "source_url": meta.get("source_url"),
            "language": meta.get("language"),
            "image_path": meta.get("image_path"),
            "text_preview": item["chunk"].page_content[:150] + "...",
            "score": item["score"],
            "from_cache": item.get("from_cache", False),
        })
    return sources


def _build_rag_messages(question: str, history: list | None, chunks: list) -> list:
    conversation = build_history(history or [], include_assistant=False, limit=6)
    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    if conversation:
        messages.append(HumanMessage(
            content=(
                "Previous user questions are provided only for conversational continuity. "
                "They are not document evidence and must not be cited or used as facts:\n"
                f"{conversation}"
            )
        ))

    if chunks:
        context = build_context(chunks)
        messages.append(HumanMessage(content=f"""Here are relevant excerpts from the currently active documents only:

{context}

Answer using these active excerpts as the only document evidence. Do not mention,
quote, cite, or rely on documents from previous chat history unless they appear
in the active excerpts above. Use your own knowledge only as supporting
explanation after answering the document fact.

Question:
{question}"""))
    else:
        messages.append(HumanMessage(
            content=f"""No relevant document excerpts found.
Answer using your own knowledge:
{question}"""
        ))
    return messages


def answer(question: str, doc_ids: list | None = None,
           session_id: str | None = None, user_id: str | None = None,
           history: list | None = None) -> dict:

    all_chunks = _retrieve_chunks(question, doc_ids, session_id, user_id)

    # Step 5 — Build messages
    messages = _build_rag_messages(question, history, all_chunks)

    response, _metadata = model_router.invoke_chat("rag_chat", messages)

    # Step 6 — Build sources
    return {"answer": response.content, "sources": _build_sources(all_chunks)}


async def chat_stream(question: str, history: list | None = None):
    conversation = build_history(history)
    messages = [SystemMessage(content=CHAT_SYSTEM_PROMPT)]

    if conversation:
        messages.append(HumanMessage(
            content=f"Previous conversation:\n{conversation}\n\nContinue naturally."
        ))
    messages.append(HumanMessage(content=question))

    async for event in model_router.stream_chat("rag_chat", messages):
        if event.get("type") == "chunk":
            yield event["content"]


async def answer_stream(question: str, doc_ids: list | None = None,
                        session_id: str | None = None, user_id: str | None = None,
                        history: list | None = None):

    all_chunks = await run_in_threadpool(_retrieve_chunks, question, doc_ids, session_id, user_id)

    # Step 3 — Build and send sources immediately
    yield {"type": "sources", "sources": _build_sources(all_chunks)}

    # Step 4 — Build messages
    messages = _build_rag_messages(question, history, all_chunks)

    # Step 5 — Stream LLM response
    async for event in model_router.stream_chat("rag_chat", messages):
        if event.get("type") == "chunk":
            yield {"type": "chunk", "content": event["content"]}
        elif event.get("type") == "error":
            yield {"type": "chunk", "content": event["content"]}
