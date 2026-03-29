# backend/api/routes/query.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from retrieval.rag_pipeline import answer
from cache.cache_manager import (
    activate_doc,
    deactivate_doc,
    get_active_doc_ids,
    get_active_docs,
    end_session,
    get_session_stats
)

router = APIRouter()

class QueryRequest(BaseModel):
    question: str
    session_id: str
    doc_ids: list[str] | None = None  # optional override, else uses active docs

class ActivateDocRequest(BaseModel):
    session_id: str
    doc_id: str
    doc_name: str

class DeactivateDocRequest(BaseModel):
    session_id: str
    doc_id: str

@router.post("/query")
async def query_documents(body: QueryRequest):
    """
    Main query route
    Uses active docs if no doc_ids provided
    """
    try:
        # Use active docs if no explicit doc_ids passed
        doc_ids = body.doc_ids
        if not doc_ids and body.session_id:
            doc_ids = get_active_doc_ids(body.session_id)

        result = answer(
            question=body.question,
            doc_ids=doc_ids if doc_ids else None,
            session_id=body.session_id
        )

        return {
            "success": True,
            "answer": result["answer"],
            "sources": result["sources"]
        }

    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/activate")
async def activate_document(body: ActivateDocRequest):
    """
    Called when user moves doc to active zone
    """
    try:
        activate_doc(body.session_id, body.doc_id, body.doc_name)
        return {
            "success": True,
            "message": f"{body.doc_name} activated"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deactivate")
async def deactivate_document(body: DeactivateDocRequest):
    """
    Called when user removes doc from active zone
    Clears cache for that doc
    """
    try:
        deactivate_doc(body.session_id, body.doc_id)
        return {
            "success": True,
            "message": "Document deactivated and cache cleared"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active/{session_id}")
async def get_active_documents(session_id: str):
    """
    Returns currently active docs for a session
    Used by frontend to sync active zone on reload
    """
    try:
        return {
            "success": True,
            "active_docs": get_active_docs(session_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def end_user_session(session_id: str):
    """
    Called when user closes app
    Clears all session cache
    """
    try:
        end_session(session_id)
        return {
            "success": True,
            "message": "Session ended and cache cleared"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{session_id}")
async def get_stats(session_id: str):
    """
    Debug route — shows active docs + cache stats
    Remove in production
    """
    try:
        return {
            "success": True,
            "stats": get_session_stats(session_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))