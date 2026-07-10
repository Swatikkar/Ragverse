# backend/retrieval/rag_pipeline.py
from langchain_core.messages import HumanMessage, SystemMessage
from retrieval.vector_store import query_chunks
from cache.cache_store import get_cached_chunks, add_to_cache
from providers import model_router
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


def chat(question: str, history: list = []) -> dict:
    conversation = build_history(history)
    messages = [SystemMessage(content=CHAT_SYSTEM_PROMPT)]

    if conversation:
        messages.append(HumanMessage(
            content=f"Previous conversation:\n{conversation}\n\nContinue naturally."
        ))
    messages.append(HumanMessage(content=question))
    response, _metadata = model_router.invoke_chat("rag_chat", messages)
    return {"answer": response.content, "sources": []}


def answer(question: str, doc_ids: list = None,
           session_id: str = None, user_id: str = None, history: list = []) -> dict:

    # Step 1 — Get cached chunks (scoped to user)
    cached_chunks = []
    cached_ids = set()

    if session_id and config.STORAGE_MODE != "supabase":
        cached_chunks = get_cached_chunks(session_id, doc_ids, user_id=user_id)
        cached_ids = {
            item["chunk"].metadata.get("chunk_id")
            for item in cached_chunks
        }

    # Step 2 — MMR search on user's collection
    new_chunks = query_chunks(
        question,
        user_id=user_id,
        n_results=8,
        doc_ids=doc_ids,
        exclude_ids=cached_ids
    )

    # Step 3 — Add to user's cache
    if session_id and new_chunks and config.STORAGE_MODE != "supabase":
        add_to_cache(session_id, new_chunks, user_id=user_id)

    # Step 4 — Merge + sort
    all_chunks = cached_chunks + new_chunks
    all_chunks = sorted(all_chunks, key=lambda x: x["score"], reverse=True)[:10]

    # Step 5 — Build messages
    conversation = build_history(history, include_assistant=False, limit=6)
    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    if conversation:
        messages.append(HumanMessage(
            content=(
                "Previous user questions are provided only for conversational continuity. "
                "They are not document evidence and must not be cited or used as facts:\n"
                f"{conversation}"
            )
        ))

    if all_chunks:
        context = build_context(all_chunks)
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
            content=f"""No relevant document excerpts found for this question.
Answer using your own knowledge:
{question}"""
        ))

    response, _metadata = model_router.invoke_chat("rag_chat", messages)

    # Step 6 — Build sources
    sources = []
    for item in all_chunks:
        meta = item["chunk"].metadata
        sources.append({
            "doc_id": meta.get("doc_id"),
            "doc_name": meta.get("doc_name") or meta.get("source"),
            "page_num": meta.get("page_num"),
            "type": meta.get("type", "text"),
            "source_type": meta.get("source_type", "document"),
            "source_url": meta.get("source_url"),
            "language": meta.get("language"),
            "image_path": meta.get("image_path"),
            "text_preview": item["chunk"].page_content[:150] + "...",
            "score": item["score"],
            "from_cache": item.get("from_cache", False)
        })

    return {"answer": response.content, "sources": sources}


async def chat_stream(question: str, history: list = []):
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


async def answer_stream(question: str, doc_ids: list = None,
                        session_id: str = None, user_id: str = None, history: list = []):

    # Step 1 — Get cached chunks (scoped to user)
    cached_chunks = []
    cached_ids = set()

    if session_id and config.STORAGE_MODE != "supabase":
        cached_chunks = get_cached_chunks(session_id, doc_ids, user_id=user_id)
        cached_ids = {
            item["chunk"].metadata.get("chunk_id")
            for item in cached_chunks
        }

    # Step 2 — Retrieve from user's collection
    new_chunks = query_chunks(
        question,
        user_id=user_id,
        n_results=8,
        doc_ids=doc_ids,
        exclude_ids=cached_ids
    )

    if session_id and new_chunks and config.STORAGE_MODE != "supabase":
        add_to_cache(session_id, new_chunks, user_id=user_id)

    all_chunks = cached_chunks + new_chunks
    all_chunks = sorted(all_chunks, key=lambda x: x["score"], reverse=True)[:10]

    # Step 3 — Build and send sources immediately
    sources = []
    for item in all_chunks:
        meta = item["chunk"].metadata
        sources.append({
            "doc_id": meta.get("doc_id"),
            "doc_name": meta.get("doc_name") or meta.get("source"),
            "page_num": meta.get("page_num"),
            "type": meta.get("type", "text"),
            "source_type": meta.get("source_type", "document"),
            "source_url": meta.get("source_url"),
            "language": meta.get("language"),
            "image_path": meta.get("image_path"),
            "text_preview": item["chunk"].page_content[:150] + "...",
            "score": item["score"],
            "from_cache": item.get("from_cache", False)
        })

    yield {"type": "sources", "sources": sources}

    # Step 4 — Build messages
    conversation = build_history(history, include_assistant=False, limit=6)
    messages = [SystemMessage(content=SYSTEM_PROMPT)]

    if conversation:
        messages.append(HumanMessage(
            content=(
                "Previous user questions are provided only for conversational continuity. "
                "They are not document evidence and must not be cited or used as facts:\n"
                f"{conversation}"
            )
        ))

    if all_chunks:
        context = build_context(all_chunks)
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

    # Step 5 — Stream LLM response
    async for event in model_router.stream_chat("rag_chat", messages):
        if event.get("type") == "chunk":
            yield {"type": "chunk", "content": event["content"]}
        elif event.get("type") == "error":
            yield {"type": "chunk", "content": event["content"]}
