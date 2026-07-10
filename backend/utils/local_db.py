from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import config


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def db_path() -> str:
    path = config.SQLITE_DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


@contextmanager
def get_connection():
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_local_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                hashed_password TEXT NOT NULL,
                full_name TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                doc_name TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'document',
                file_type TEXT,
                source_url TEXT,
                status TEXT NOT NULL DEFAULT 'indexed',
                storage_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS document_artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                artifact_type TEXT NOT NULL,
                storage_path TEXT,
                content_type TEXT,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS document_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL DEFAULT 0,
                type TEXT NOT NULL DEFAULT 'text',
                content TEXT,
                text_preview TEXT,
                metadata TEXT,
                embedding TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(doc_id, chunk_id)
            );

            CREATE TABLE IF NOT EXISTS chat_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS active_documents (
                session_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                doc_name TEXT NOT NULL,
                activated_at TEXT NOT NULL,
                PRIMARY KEY(session_id, user_id, doc_id),
                FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
            CREATE INDEX IF NOT EXISTS idx_artifacts_user_doc ON document_artifacts(user_id, doc_id);
            CREATE INDEX IF NOT EXISTS idx_chunks_user_doc ON document_chunks(user_id, doc_id);
            CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_active_documents_session ON active_documents(user_id, session_id);
            """
        )
        for statement in [
            "ALTER TABLE document_chunks ADD COLUMN content TEXT",
            "ALTER TABLE document_chunks ADD COLUMN metadata TEXT",
            "ALTER TABLE document_chunks ADD COLUMN embedding TEXT",
        ]:
            try:
                conn.execute(statement)
            except sqlite3.OperationalError:
                pass


init_local_db()
