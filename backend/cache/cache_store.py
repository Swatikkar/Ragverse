# backend/cache/cache_store.py
from datetime import datetime

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


def _key(user_id: str, session_id: str) -> str:
    return f"{user_id}:{session_id}"


def get_cached_chunks(session_id: str, doc_ids: list = None, user_id: str = None) -> list:
    cache_key = _key(user_id, session_id) if user_id else session_id
    if cache_key not in _cache:
        return []

    cached_chunks = []
    session = _cache[cache_key]

    for doc_id, data in session.items():
        if doc_ids and doc_id not in doc_ids:
            continue

        for chunk in data["chunks"]:
            cached_chunks.append({
                "chunk": chunk["chunk"],
                "score": chunk["score"],
                "from_cache": True
            })

        data["last_accessed"] = datetime.now()

    return cached_chunks


def add_to_cache(session_id: str, chunks: list, user_id: str = None):
    cache_key = _key(user_id, session_id) if user_id else session_id
    if cache_key not in _cache:
        _cache[cache_key] = {}

    session = _cache[cache_key]

    for item in chunks:
        doc_id = item["chunk"].metadata["doc_id"]

        if doc_id not in session:
            session[doc_id] = {
                "chunks": [],
                "activated_at": datetime.now(),
                "last_accessed": datetime.now()
            }

        existing_ids = {
            c["chunk"].metadata.get("chunk_id")
            for c in session[doc_id]["chunks"]
        }

        if item["chunk"].metadata.get("chunk_id") not in existing_ids:
            session[doc_id]["chunks"].append({
                "chunk": item["chunk"],
                "score": item["score"]
            })


def clear_doc_cache(session_id: str, doc_id: str, user_id: str = None):
    cache_key = _key(user_id, session_id) if user_id else session_id
    if cache_key in _cache and doc_id in _cache[cache_key]:
        del _cache[cache_key][doc_id]


def clear_session_cache(session_id: str, user_id: str = None):
    cache_key = _key(user_id, session_id) if user_id else session_id
    if cache_key in _cache:
        del _cache[cache_key]


def get_cache_stats(session_id: str, user_id: str = None) -> dict:
    cache_key = _key(user_id, session_id) if user_id else session_id
    if cache_key not in _cache:
        return {}

    return {
        doc_id: {
            "chunk_count": len(data["chunks"]),
            "activated_at": data["activated_at"].isoformat(),
            "last_accessed": data["last_accessed"].isoformat()
        }
        for doc_id, data in _cache[cache_key].items()
    }