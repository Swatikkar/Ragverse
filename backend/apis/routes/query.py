# backend/api/routes/query.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from retrieval.rag_pipeline import chat_stream, answer_stream
from cache.cache_manager import (
    activate_doc,
    deactivate_doc,
    get_active_doc_ids,
    get_active_docs,
    end_session,
)
from auth.dependencies import get_current_user
from utils.supabase_store import (
    activate_document_for_session,
    add_chat_message,
    deactivate_document_for_session,
    end_chat_session,
    ensure_chat_session,
    list_active_documents,
    list_chat_messages,
)
import json

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    session_id: str
    doc_ids: list[str] | None = None
    history: list[dict] | None = []


class ActivateDocRequest(BaseModel):
    session_id: str
    doc_id: str
    doc_name: str


class DeactivateDocRequest(BaseModel):
    session_id: str
    doc_id: str


@router.post("/query")
async def query_documents(
    body: QueryRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]

    try:
        ensure_chat_session(user_id, body.session_id, title=body.question[:80])
        add_chat_message(user_id, body.session_id, "user", body.question)
        # Treat the persisted active-document table as the source of truth.
        # Browser state can lag behind rapid activate/deactivate clicks, so
        # trusting request doc_ids can retrieve stale or missing sources.
        persisted_active = list_active_documents(user_id, body.session_id) if body.session_id else []
        doc_ids = [doc["doc_id"] for doc in persisted_active]
        if not doc_ids:
            doc_ids = get_active_doc_ids(body.session_id, user_id=user_id) if body.session_id else (body.doc_ids or [])

        if not doc_ids:
            async def stream_chat():
                sources = []
                answer_parts = []
                async for chunk in chat_stream(body.question, history=body.history or []):
                    answer_parts.append(chunk)
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
                add_chat_message(user_id, body.session_id, "assistant", "".join(answer_parts), sources)
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                stream_chat(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
            )
        else:
            async def stream_rag():
                answer_parts = []
                sources = []
                async for event in answer_stream(
                    question=body.question,
                    doc_ids=doc_ids,
                    session_id=body.session_id,
                    user_id=user_id,
                    history=body.history or []
                ):
                    if event.get("type") == "chunk":
                        answer_parts.append(event.get("content", ""))
                    elif event.get("type") == "sources":
                        sources = event.get("sources", [])
                    yield f"data: {json.dumps(event)}\n\n"
                add_chat_message(user_id, body.session_id, "assistant", "".join(answer_parts), sources)
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                stream_rag(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
            )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/activate")
async def activate_document(
    body: ActivateDocRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    try:
        activate_doc(body.session_id, body.doc_id, body.doc_name, user_id=user_id)
        activate_document_for_session(user_id, body.session_id, body.doc_id, body.doc_name)
        return {"success": True, "message": f"{body.doc_name} activated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deactivate")
async def deactivate_document(
    body: DeactivateDocRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    try:
        deactivate_doc(body.session_id, body.doc_id, user_id=user_id)
        deactivate_document_for_session(user_id, body.session_id, body.doc_id)
        return {"success": True, "message": "Document deactivated and cache cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active/{session_id}")
async def get_active_documents(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    try:
        active_docs = list_active_documents(user_id, session_id) or get_active_docs(session_id, user_id=user_id)
        return {"success": True, "active_docs": active_docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def end_user_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    try:
        end_session(session_id, user_id=user_id)
        end_chat_session(user_id, session_id)
        return {"success": True, "message": "Session ended and cache cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/{session_id}")
async def get_chat_messages(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    try:
        restored_session_id, messages = list_chat_messages(user_id, session_id=session_id)
        return {"success": True, "session_id": restored_session_id or session_id, "messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat")
async def get_latest_chat(
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]
    try:
        session_id, messages = list_chat_messages(user_id)
        return {"success": True, "session_id": session_id, "messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
