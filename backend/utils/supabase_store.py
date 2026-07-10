from __future__ import annotations

import os
import json
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
                INSERT OR IGNORE INTO document_chunks (doc_id, user_id, chunk_id, chunk_index, type, content, text_preview, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metadata["doc_id"],
                    metadata["user_id"],
                    chunk_meta.get("chunk_id"),
                    int(chunk_meta.get("chunk_index") or 0),
                    chunk_meta.get("type", "text"),
                    chunk.page_content,
                    chunk.page_content[:300],
                    json.dumps(chunk_meta),
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

    if chunks:
        upsert_document_chunks(metadata["user_id"], chunks)


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


def _list_storage_paths(prefix: str) -> list[str]:
    client = get_supabase()
    if not client:
        return []

    paths = []
    entries = client.storage.from_(config.SUPABASE_BUCKET).list(prefix)
    for item in entries:
        name = item.get("name")
        if not name:
            continue
        path = f"{prefix}/{name}" if prefix else name
        if item.get("metadata") is None:
            paths.extend(_list_storage_paths(path))
        else:
            paths.append(path)
    return paths


def delete_user_artifacts(user_id: str) -> None:
    if config.STORAGE_MODE == "supabase":
        client = get_supabase()
        if client:
            try:
                paths = _list_storage_paths(user_id)
                if paths:
                    client.storage.from_(config.SUPABASE_BUCKET).remove(paths)
            except Exception as exc:
                print(f"[supabase] user artifact delete skipped: {exc}", flush=True)
            return


def list_documents(user_id: str) -> list[dict]:
    if config.STORAGE_MODE == "supabase":
        client = get_supabase()
        if client:
            response = (
                client.table("documents")
                .select("doc_id,doc_name,source_type,file_type,source_url,status,created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )
            return response.data or []

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT doc_id, doc_name, source_type, file_type, source_url, status, created_at
            FROM documents
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def normalize_embedding(embedding: list[float] | None) -> list[float] | None:
    if embedding is None:
        return None
    values = [float(value) for value in embedding]
    dim = config.EMBEDDING_DIMENSION
    if len(values) == dim:
        return values
    if len(values) > dim:
        return values[:dim]
    return values + [0.0] * (dim - len(values))


def _chunk_row(user_id: str, chunk, embedding: list[float] | None = None) -> dict:
    metadata = dict(chunk.metadata or {})
    return {
        "doc_id": metadata.get("doc_id"),
        "user_id": user_id,
        "chunk_id": metadata.get("chunk_id"),
        "chunk_index": int(metadata.get("chunk_index") or 0),
        "type": metadata.get("type", "text"),
        "content": chunk.page_content,
        "text_preview": chunk.page_content[:300],
        "metadata": metadata,
        "embedding": normalize_embedding(embedding),
    }


def upsert_document_chunks(user_id: str, chunks: list, embeddings: list[list[float]] | None = None) -> None:
    if not chunks:
        return

    if config.STORAGE_MODE == "supabase":
        client = get_supabase()
        if client:
            rows = [
                _chunk_row(user_id, chunk, embeddings[index] if embeddings else None)
                for index, chunk in enumerate(chunks)
                if chunk.metadata.get("doc_id") and chunk.metadata.get("chunk_id")
            ]
            if rows:
                client.table("document_chunks").upsert(rows, on_conflict="doc_id,chunk_id").execute()
            return

    now = utc_now()
    with get_connection() as conn:
        for index, chunk in enumerate(chunks):
            row = _chunk_row(user_id, chunk, embeddings[index] if embeddings else None)
            conn.execute(
                """
                INSERT INTO document_chunks (doc_id, user_id, chunk_id, chunk_index, type, content, text_preview, metadata, embedding, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(doc_id, chunk_id) DO UPDATE SET
                    content = excluded.content,
                    text_preview = excluded.text_preview,
                    metadata = excluded.metadata,
                    embedding = excluded.embedding
                """,
                (
                    row["doc_id"],
                    row["user_id"],
                    row["chunk_id"],
                    row["chunk_index"],
                    row["type"],
                    row["content"],
                    row["text_preview"],
                    json.dumps(row["metadata"]),
                    json.dumps(row["embedding"]),
                    now,
                ),
            )


def ensure_chat_session(user_id: str, session_id: str, title: str | None = None) -> None:
    now = utc_now()
    if config.STORAGE_MODE == "supabase":
        client = get_supabase()
        if client:
            row = {
                "session_id": session_id,
                "user_id": user_id,
                "updated_at": now,
            }
            if title:
                row["title"] = title
            client.table("chat_sessions").upsert(row, on_conflict="session_id").execute()
            return

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_sessions (session_id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                title = COALESCE(excluded.title, chat_sessions.title),
                updated_at = excluded.updated_at
            """,
            (session_id, user_id, title, now, now),
        )


def add_chat_message(user_id: str, session_id: str, role: str, content: str, sources: list | None = None) -> None:
    ensure_chat_session(user_id, session_id, title=content[:80] if role == "user" else None)
    row = {
        "session_id": session_id,
        "user_id": user_id,
        "role": role,
        "content": content,
        "sources": sources or [],
    }
    if config.STORAGE_MODE == "supabase":
        client = get_supabase()
        if client:
            client.table("chat_messages").insert(row).execute()
            client.table("chat_sessions").update({"updated_at": utc_now()}).eq("session_id", session_id).eq("user_id", user_id).execute()
            return

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO chat_messages (session_id, user_id, role, content, sources, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, user_id, role, content, json.dumps(sources or []), utc_now()),
        )
        conn.execute(
            "UPDATE chat_sessions SET updated_at = ? WHERE session_id = ? AND user_id = ?",
            (utc_now(), session_id, user_id),
        )


def list_chat_messages(user_id: str, session_id: str | None = None, limit: int = 100) -> tuple[str | None, list[dict]]:
    if config.STORAGE_MODE == "supabase":
        client = get_supabase()
        if client:
            if not session_id:
                sessions = (
                    client.table("chat_sessions")
                    .select("session_id")
                    .eq("user_id", user_id)
                    .order("updated_at", desc=True)
                    .limit(1)
                    .execute()
                )
                session_id = sessions.data[0]["session_id"] if sessions.data else None
            if not session_id:
                return None, []
            messages = (
                client.table("chat_messages")
                .select("role,content,sources,created_at")
                .eq("user_id", user_id)
                .eq("session_id", session_id)
                .order("created_at")
                .limit(limit)
                .execute()
            )
            return session_id, messages.data or []

    with get_connection() as conn:
        if not session_id:
            row = conn.execute(
                "SELECT session_id FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1",
                (user_id,),
            ).fetchone()
            session_id = row["session_id"] if row else None
        if not session_id:
            return None, []
        rows = conn.execute(
            """
            SELECT role, content, sources, created_at
            FROM chat_messages
            WHERE user_id = ? AND session_id = ?
            ORDER BY created_at
            LIMIT ?
            """,
            (user_id, session_id, limit),
        ).fetchall()
        return session_id, [
            {
                "role": row["role"],
                "content": row["content"],
                "sources": json.loads(row["sources"] or "[]"),
                "created_at": row["created_at"],
            }
            for row in rows
        ]


def activate_document_for_session(user_id: str, session_id: str, doc_id: str, doc_name: str) -> None:
    ensure_chat_session(user_id, session_id)
    now = utc_now()
    if config.STORAGE_MODE == "supabase":
        client = get_supabase()
        if client:
            client.table("active_documents").upsert(
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "doc_id": doc_id,
                    "doc_name": doc_name,
                    "activated_at": now,
                },
                on_conflict="session_id,user_id,doc_id",
            ).execute()
            return

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO active_documents (session_id, user_id, doc_id, doc_name, activated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(session_id, user_id, doc_id) DO UPDATE SET
                doc_name = excluded.doc_name,
                activated_at = excluded.activated_at
            """,
            (session_id, user_id, doc_id, doc_name, now),
        )


def deactivate_document_for_session(user_id: str, session_id: str, doc_id: str) -> None:
    if config.STORAGE_MODE == "supabase":
        client = get_supabase()
        if client:
            client.table("active_documents").delete().eq("user_id", user_id).eq("session_id", session_id).eq("doc_id", doc_id).execute()
            return

    with get_connection() as conn:
        conn.execute(
            "DELETE FROM active_documents WHERE user_id = ? AND session_id = ? AND doc_id = ?",
            (user_id, session_id, doc_id),
        )


def list_active_documents(user_id: str, session_id: str) -> list[dict]:
    if config.STORAGE_MODE == "supabase":
        client = get_supabase()
        if client:
            response = (
                client.table("active_documents")
                .select("doc_id,doc_name,activated_at")
                .eq("user_id", user_id)
                .eq("session_id", session_id)
                .order("activated_at", desc=False)
                .execute()
            )
            return response.data or []

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT doc_id, doc_name, activated_at
            FROM active_documents
            WHERE user_id = ? AND session_id = ?
            ORDER BY activated_at
            """,
            (user_id, session_id),
        ).fetchall()
        return [dict(row) for row in rows]


def end_chat_session(user_id: str, session_id: str) -> None:
    if config.STORAGE_MODE == "supabase":
        client = get_supabase()
        if client:
            client.table("active_documents").delete().eq("user_id", user_id).eq("session_id", session_id).execute()
            return

    with get_connection() as conn:
        conn.execute(
            "DELETE FROM active_documents WHERE user_id = ? AND session_id = ?",
            (user_id, session_id),
        )


def safe_persist_document(metadata: dict, artifacts: list[dict], chunks: list | None = None) -> None:
    try:
        if config.STORAGE_MODE == "supabase":
            _persist_supabase(metadata, artifacts, chunks)
        else:
            _persist_local(metadata, artifacts, chunks)
    except Exception as exc:
        print(f"[metadata] persistence skipped: {exc}", flush=True)
