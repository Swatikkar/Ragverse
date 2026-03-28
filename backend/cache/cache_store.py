# backend/cache/cache_store.py
from datetime import datetime

# In memory cache structure:
# {
#   session_id: {
#       doc_id: {
#           "chunks": [...],
#           "activated_at": datetime,
#           "last_accessed": datetime
#       }
#   }
# }

_cache: dict = {}

def get_cached_chunks(session_id: str, doc_ids: list = None) -> list:
    """
    Returns cached chunks for a session
    Optionally filtered by doc_ids
    """
    if session_id not in _cache:
        return []

    cached_chunks = []
    session = _cache[session_id]

    for doc_id, data in session.items():
        # Skip if doc_id filter provided and this doc not in it
        if doc_ids and doc_id not in doc_ids:
            continue

        for chunk in data["chunks"]:
            cached_chunks.append({
                "chunk": chunk["chunk"],
                "score": chunk["score"],
                "from_cache": True      # flag for frontend
            })

        # Update last accessed time
        data["last_accessed"] = datetime.now()

    return cached_chunks

def add_to_cache(session_id: str, chunks: list):
    """
    Adds newly retrieved chunks to session cache
    Organized by doc_id for easy cleanup
    """
    if session_id not in _cache:
        _cache[session_id] = {}

    session = _cache[session_id]

    for item in chunks:
        doc_id = item["chunk"].metadata["doc_id"]

        if doc_id not in session:
            session[doc_id] = {
                "chunks": [],
                "activated_at": datetime.now(),
                "last_accessed": datetime.now()
            }

        # Avoid duplicate chunks
        existing_ids = {
            c["chunk"].metadata.get("chunk_id")
            for c in session[doc_id]["chunks"]
        }

        if item["chunk"].metadata.get("chunk_id") not in existing_ids:
            session[doc_id]["chunks"].append({
                "chunk": item["chunk"],
                "score": item["score"]
            })

def clear_doc_cache(session_id: str, doc_id: str):
    """
    Called when user removes doc from active zone
    Clears all cached chunks for that doc in this session
    """
    if session_id in _cache and doc_id in _cache[session_id]:
        del _cache[session_id][doc_id]

def clear_session_cache(session_id: str):
    """
    Called when session ends
    Clears entire session cache
    """
    if session_id in _cache:
        del _cache[session_id]

def get_cache_stats(session_id: str) -> dict:
    """
    Useful for debugging — shows cache size per doc
    """
    if session_id not in _cache:
        return {}

    return {
        doc_id: {
            "chunk_count": len(data["chunks"]),
            "activated_at": data["activated_at"].isoformat(),
            "last_accessed": data["last_accessed"].isoformat()
        }
        for doc_id, data in _cache[session_id].items()
    }