from __future__ import annotations

import os
from pathlib import Path

from supabase import Client, create_client

import config
from utils.local_db import get_connection, utc_now


_client: Client | None = None


def get_supabase() -> Client | None:
    global _client
    if config.STORAGE_MODE != "supabase":
        return None
    if _client is None and config.SUPABASE_URL and config.SUPABASE_KEY:
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _client


def upload_file(path: str, storage_path: str, content_type: str | None = None) -> str | None:
    client = get_supabase()
    if not client:
        return storage_path
    data = Path(path).read_bytes()
    options = {"content-type": content_type} if content_type else None
    client.storage.from_(config.SUPABASE_BUCKET).upload(storage_path, data, file_options=options)
    return storage_path


def upload_text(text: str, storage_path: str, content_type: str = "text/plain") -> str | None:
    client = get_supabase()
    if not client:
        return storage_path
    client.storage.from_(config.SUPABASE_BUCKET).upload(
        storage_path,
        text.encode("utf-8"),
        file_options={"content-type": content_type},
    )
    return storage_path


def _artifact_size(artifact: dict) -> int:
    if artifact.get("kind") == "file" and artifact.get("path"):
        try:
            return os.path.getsize(artifact["path"])
        except OSError:
            return 0
    if artifact.get("kind") == "text":
        return len((artifact.get("text") or "").encode("utf-8"))
    return 0


def _persist_local(metadata: dict, artifacts: list[dict], chunks: list | None = None) -> None:
    now = utc_now()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO documents (doc_id, user_id, doc_name, source_type, file_type, source_url, status, storage_path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(doc_id) DO UPDATE SET
                doc_name = excluded.doc_name,
                source_type = excluded.source_type,
                file_type = excluded.file_type,
                source_url = excluded.source_url,
                status = excluded.status,
                storage_path = excluded.storage_path,
                updated_at = excluded.updated_at
            """,
            (
                metadata["doc_id"],
                metadata["user_id"],
                metadata["doc_name"],
                metadata.get("source_type", "document"),
                metadata.get("file_type"),
                metadata.get("source_url"),
                metadata.get("status", "indexed"),
                metadata.get("storage_path"),
                now,
                now,
            ),
        )

        for artifact in artifacts:
            conn.execute(
                """
                INSERT INTO document_artifacts (doc_id, user_id, artifact_type, storage_path, content_type, size_bytes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metadata["doc_id"],
                    metadata["user_id"],
                    artifact.get("artifact_type") or artifact.get("kind", "artifact"),
                    artifact.get("storage_path"),
                    artifact.get("content_type"),
                    _artifact_size(artifact),
                    now,
                ),
            )

        for chunk in chunks or []:
            chunk_meta = chunk.metadata
            conn.execute(
                """
                INSERT OR IGNORE INTO document_chunks (doc_id, user_id, chunk_id, chunk_index, type, text_preview, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metadata["doc_id"],
                    metadata["user_id"],
                    chunk_meta.get("chunk_id"),
                    int(chunk_meta.get("chunk_index") or 0),
                    chunk_meta.get("type", "text"),
                    chunk.page_content[:300],
                    now,
                ),
            )


def _persist_supabase(metadata: dict, artifacts: list[dict], chunks: list | None = None) -> None:
    client = get_supabase()
    if not client:
        return

    for artifact in artifacts:
        kind = artifact.get("kind")
        if kind == "file":
            upload_file(artifact["path"], artifact["storage_path"], artifact.get("content_type"))
        elif kind == "text":
            upload_text(artifact["text"], artifact["storage_path"], artifact.get("content_type", "text/plain"))

    client.table("documents").upsert(metadata).execute()

    artifact_rows = [
        {
            "doc_id": metadata["doc_id"],
            "user_id": metadata["user_id"],
            "artifact_type": artifact.get("artifact_type") or artifact.get("kind", "artifact"),
            "storage_path": artifact.get("storage_path"),
            "content_type": artifact.get("content_type"),
            "size_bytes": _artifact_size(artifact),
        }
        for artifact in artifacts
    ]
    if artifact_rows:
        client.table("document_artifacts").insert(artifact_rows).execute()

    chunk_rows = [
        {
            "doc_id": metadata["doc_id"],
            "user_id": metadata["user_id"],
            "chunk_id": chunk.metadata.get("chunk_id"),
            "chunk_index": int(chunk.metadata.get("chunk_index") or 0),
            "type": chunk.metadata.get("type", "text"),
            "text_preview": chunk.page_content[:300],
        }
        for chunk in chunks or []
        if chunk.metadata.get("chunk_id")
    ]
    if chunk_rows:
        client.table("document_chunks").upsert(chunk_rows).execute()


def delete_document_artifacts(user_id: str, doc_id: str) -> None:
    if config.STORAGE_MODE == "supabase":
        client = get_supabase()
        if client:
            prefix = f"{user_id}/{doc_id}"
            try:
                files = client.storage.from_(config.SUPABASE_BUCKET).list(prefix)
                paths = [f"{prefix}/{item['name']}" for item in files]
                if paths:
                    client.storage.from_(config.SUPABASE_BUCKET).remove(paths)
            except Exception as exc:
                print(f"[supabase] artifact delete skipped: {exc}", flush=True)
            try:
                client.table("documents").delete().eq("user_id", user_id).eq("doc_id", doc_id).execute()
            except Exception as exc:
                print(f"[supabase] metadata delete skipped: {exc}", flush=True)
            return

    with get_connection() as conn:
        conn.execute("DELETE FROM documents WHERE user_id = ? AND doc_id = ?", (user_id, doc_id))


def safe_persist_document(metadata: dict, artifacts: list[dict], chunks: list | None = None) -> None:
    try:
        if config.STORAGE_MODE == "supabase":
            _persist_supabase(metadata, artifacts, chunks)
        else:
            _persist_local(metadata, artifacts, chunks)
    except Exception as exc:
        print(f"[metadata] persistence skipped: {exc}", flush=True)
