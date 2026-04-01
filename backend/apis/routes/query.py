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
@router.post("/query")
async def query_documents(body: QueryRequest):
    try:
        doc_ids = body.doc_ids
        if not doc_ids and body.session_id:
            doc_ids = get_active_doc_ids(body.session_id)

        # No active docs → normal chat mode
        if not doc_ids:
            from retrieval.rag_pipeline import chat
            result = chat(body.question, history=body.history or [])
        else:
            result = answer(
                question=body.question,
                doc_ids=doc_ids,
                session_id=body.session_id,
                history=body.history or []
            )

        return {
            "success": True,
            "answer": result["answer"],
            "sources": result["sources"]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/activate")
async def activate_document(body: ActivateDocRequest):
    
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
  
    try:
        return {
            "success": True,
            "active_docs": get_active_docs(session_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def end_user_session(session_id: str):
  
    try:
        end_session(session_id)
        return {
            "success": True,
            "message": "Session ended and cache cleared"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# @router.get("/debug/{doc_id}")
# async def debug_document(doc_id: str):
#     from retrieval.vector_store import vector_store
#     results = vector_store.get(where={"doc_id": {"$eq": doc_id}})
#     return {
#         "total_chunks": len(results["documents"]),
#         "chunks": [
#             {
#                 "text": doc[:200],
#                 "metadata": meta
#             }
#             for doc, meta in zip(results["documents"], results["metadatas"])
#         ]
#     }