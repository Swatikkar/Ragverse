# backend/api/routes/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel, HttpUrl
from starlette.concurrency import run_in_threadpool
from utils.file_handler import save_upload, delete_upload
from ingestion.orchestrator import process_document
from ingestion.url_loader import load_url
from ingestion.chunker import chunk_documents
from retrieval.vector_store import store_chunks, delete_document
from cache.cache_manager import deactivate_doc
from auth.dependencies import get_current_user
from utils.supabase_store import delete_document_artifacts, list_documents, persist_document
import uuid
import os

router = APIRouter()


def _cleanup_failed_document(doc_id: str, user_id: str) -> None:
    for action, args in (
        (delete_document, (doc_id, user_id)),
        (delete_document_artifacts, (user_id, doc_id)),
        (delete_upload, (doc_id, user_id)),
    ):
        try:
            action(*args)
        except Exception as exc:
            print(f"[upload-cleanup] {action.__name__} failed: {exc}", flush=True)


class UrlIngestRequest(BaseModel):
    url: HttpUrl


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    doc_id = str(uuid.uuid4())
    user_id = current_user["user_id"]

    try:
        # Step 1 — Save file to disk (scoped by user_id/doc_id)
        file_path = await save_upload(file, doc_id, user_id)

        # Step 2 — Process document (extract, chunk, describe images)
        result = await run_in_threadpool(process_document, file_path, doc_id, user_id)

        # Step 3 — Store chunks in user's ChromaDB collection
        file_type = os.path.splitext(file_path)[-1].lower().lstrip(".")
        source_type = result["chunks"][0].metadata.get("source_type", "document") if result["chunks"] else "document"
        storage_path = f"{user_id}/{doc_id}/{os.path.basename(file_path)}"
        await run_in_threadpool(
            persist_document,
            {
                "doc_id": doc_id,
                "user_id": user_id,
                "doc_name": os.path.basename(file_path),
                "source_type": source_type,
                "file_type": file_type,
                "storage_path": storage_path,
            },
            [{"kind": "file", "path": file_path, "storage_path": storage_path}],
        )
        stored = await run_in_threadpool(store_chunks, result["chunks"], user_id)

        return {
            "success": True,
            "doc_id": doc_id,
            "doc_name": os.path.basename(file_path),
            "source_type": source_type,
            "file_type": file_type,
            "text_chunks": result["text_chunks"],
            "image_chunks": result["image_chunks"],
            "total_indexed": stored
        }

    except HTTPException:
        await run_in_threadpool(_cleanup_failed_document, doc_id, user_id)
        raise
    except Exception as e:
        await run_in_threadpool(_cleanup_failed_document, doc_id, user_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/document/{doc_id}")
async def delete_document_route(
    doc_id: str,
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["user_id"]

    try:
        await run_in_threadpool(delete_document, doc_id, user_id)
        await run_in_threadpool(delete_upload, doc_id, user_id)
        await run_in_threadpool(delete_document_artifacts, user_id, doc_id)
        await run_in_threadpool(deactivate_doc, session_id, doc_id, user_id)

        return {
            "success": True,
            "doc_id": doc_id,
            "message": "Document deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/url")
async def ingest_url(
    body: UrlIngestRequest,
    current_user: dict = Depends(get_current_user),
):
    doc_id = str(uuid.uuid4())
    user_id = current_user["user_id"]

    try:
        pages, url_info = await run_in_threadpool(load_url, str(body.url), doc_id)
        chunks = await run_in_threadpool(chunk_documents, pages)
        storage_path = f"{user_id}/{doc_id}/extracted_url.txt"
        await run_in_threadpool(
            persist_document,
            {
                "doc_id": doc_id,
                "user_id": user_id,
                "doc_name": url_info["doc_name"],
                "source_type": "url",
                "file_type": "url",
                "source_url": url_info["source_url"],
                "storage_path": storage_path,
            },
            [{"kind": "text", "text": url_info["text"], "storage_path": storage_path}],
        )
        stored = await run_in_threadpool(store_chunks, chunks, user_id)

        return {
            "success": True,
            "doc_id": doc_id,
            "doc_name": url_info["doc_name"],
            "source_type": "url",
            "file_type": "url",
            "source_url": url_info["source_url"],
            "text_chunks": len(chunks),
            "image_chunks": 0,
            "total_indexed": stored,
        }
    except HTTPException:
        await run_in_threadpool(_cleanup_failed_document, doc_id, user_id)
        raise
    except Exception as e:
        await run_in_threadpool(_cleanup_failed_document, doc_id, user_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def get_documents(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]

    try:
        documents = await run_in_threadpool(list_documents, user_id)
        return {
            "success": True,
            "documents": documents
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
