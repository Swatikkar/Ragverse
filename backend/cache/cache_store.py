# backend/cache/cache_store.py
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from threading import RLock
from time import monotonic

# Cache structure:
# {
#   "{user_id}:{session_id}": {
#       doc_id: {
#           "chunks": [...],
#           "activated_at": datetime,
#           "last_accessed": datetime
#       }
#   }
# }

_cache: dict = {}
_lock = RLock()
_cache_ttl_seconds = 600
_max_queries_per_session = 32


def _key(user_id: str, session_id: str) -> str:
    return f"{user_id}:{session_id}"


def _query_key(question: str, doc_ids: list | None) -> str:
    normalized_question = " ".join((question or "").casefold().split())
    normalized_docs = ",".join(sorted(str(doc_id) for doc_id in (doc_ids or [])))
    return sha256(f"{normalized_docs}\n{normalized_question}".encode("utf-8")).hexdigest()


def _prune_session(session: dict) -> None:
    now = monotonic()
    expired = [key for key, value in session.items() if now - value["last_accessed"] > _cache_ttl_seconds]
    for key in expired:
        session.pop(key, None)

    overflow = len(session) - _max_queries_per_session
    if overflow > 0:
        oldest = sorted(session, key=lambda key: session[key]["last_accessed"])[:overflow]
        for key in oldest:
            session.pop(key, None)


def get_cached_chunks(
    session_id: str,
    question: str,
    doc_ids: list | None = None,
    user_id: str | None = None,
) -> list:
    cache_key = _key(user_id, session_id) if user_id else session_id
    query_key = _query_key(question, doc_ids)
    with _lock:
        session = _cache.get(cache_key)
        if not session:
            return []
        _prune_session(session)
        entry = session.get(query_key)
        if not entry:
            return []
        entry["last_accessed"] = monotonic()
        return [
            {"chunk": item["chunk"], "score": item["score"], "from_cache": True}
            for item in entry["chunks"]
        ]


def add_to_cache(
    session_id: str,
    question: str,
    doc_ids: list | None,
    chunks: list,
    user_id: str | None = None,
):
    cache_key = _key(user_id, session_id) if user_id else session_id
    query_key = _query_key(question, doc_ids)
    with _lock:
        session = _cache.setdefault(cache_key, {})
        session[query_key] = {
            "chunks": [{"chunk": item["chunk"], "score": item["score"]} for item in chunks],
            "doc_ids": {str(doc_id) for doc_id in (doc_ids or [])},
            "created_at": datetime.now(),
            "last_accessed": monotonic(),
        }
        _prune_session(session)


def clear_doc_cache(session_id: str, doc_id: str, user_id: str = None):
    cache_key = _key(user_id, session_id) if user_id else session_id
    with _lock:
        session = _cache.get(cache_key)
        if not session:
            return
        stale_keys = [key for key, value in session.items() if str(doc_id) in value["doc_ids"]]
        for key in stale_keys:
            session.pop(key, None)


def clear_session_cache(session_id: str, user_id: str = None):
    cache_key = _key(user_id, session_id) if user_id else session_id
    with _lock:
        _cache.pop(cache_key, None)


def get_cache_stats(session_id: str, user_id: str = None) -> dict:
    cache_key = _key(user_id, session_id) if user_id else session_id
    with _lock:
        session = _cache.get(cache_key)
        if not session:
            return {}
        _prune_session(session)
        return {
            "query_count": len(session),
            "chunk_count": sum(len(value["chunks"]) for value in session.values()),
            "ttl_seconds": _cache_ttl_seconds,
        }
