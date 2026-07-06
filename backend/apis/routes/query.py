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
        doc_ids = body.doc_ids
        if not doc_ids and body.session_id:
            doc_ids = get_active_doc_ids(body.session_id, user_id=user_id)

        if not doc_ids:
            async def stream_chat():
                sources = []
                async for chunk in chat_stream(body.question, history=body.history or []):
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                stream_chat(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
            )
        else:
            async def stream_rag():
                async for event in answer_stream(
                    question=body.question,
                    doc_ids=doc_ids,
                    session_id=body.session_id,
                    user_id=user_id,
                    history=body.history or []
                ):
                    yield f"data: {json.dumps(event)}\n\n"
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
        return {"success": True, "active_docs": get_active_docs(session_id, user_id=user_id)}
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
        return {"success": True, "message": "Session ended and cache cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))