# backend/api/routes/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from utils.file_handler import save_upload, delete_upload
from ingestion.orchestrator import process_document
from retrieval.vector_store import store_chunks, delete_document
from cache.cache_manager import deactivate_doc
import uuid

router = APIRouter()

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Handles file upload, processing and indexing
    Returns doc_id and processing stats
    """
    doc_id = str(uuid.uuid4())

    try:
        # Step 1 — Save file to disk
        file_path = await save_upload(file, doc_id)

        # Step 2 — Process document (extract, chunk, describe images)
        result = process_document(file_path, doc_id)

        # Step 3 — Store chunks in ChromaDB
        stored = store_chunks(result["chunks"])

        return {
            "success": True,
            "doc_id": doc_id,
            "doc_name": file.filename,
            "text_chunks": result["text_chunks"],
            "image_chunks": result["image_chunks"],
            "total_indexed": stored
        }

    except Exception as e:
        # Cleanup if anything fails
        delete_upload(doc_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/document/{doc_id}")
async def delete_document_route(doc_id: str, session_id: str):
    """
    Deletes document from ChromaDB, disk and cache
    """
    try:
        # Remove from ChromaDB
        delete_document(doc_id)

        # Remove files from disk
        delete_upload(doc_id)

        # Clear from active zone cache
        deactivate_doc(session_id, doc_id)

        return {
            "success": True,
            "doc_id": doc_id,
            "message": "Document deleted successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def get_documents():
    """
    Returns list of all indexed documents
    Used to populate document library in frontend
    """
    from retrieval.vector_store import vector_store

    try:
        # Get unique documents from ChromaDB
        results = vector_store.get()
        seen = {}

        for metadata in results["metadatas"]:
            doc_id = metadata.get("doc_id")
            if doc_id and doc_id not in seen:
                seen[doc_id] = {
                    "doc_id": doc_id,
                    "doc_name": metadata.get("doc_name"),
                    "file_type": metadata.get("file_type")
                }

        return {
            "success": True,
            "documents": list(seen.values())
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))