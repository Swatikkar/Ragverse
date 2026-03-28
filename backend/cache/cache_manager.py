# backend/cache/cache_manager.py
from cache.cache_store import clear_doc_cache, clear_session_cache, get_cache_stats
from datetime import datetime

# Tracks which docs are active per session
# {
#   session_id: {
#       doc_id: {
#           "activated_at": datetime,
#           "doc_name": str
#       }
#   }
# }

_active_docs: dict = {}

def activate_doc(session_id: str, doc_id: str, doc_name: str):
    """
    Called when user moves doc to active zone in frontend
    """
    if session_id not in _active_docs:
        _active_docs[session_id] = {}

    _active_docs[session_id][doc_id] = {
        "activated_at": datetime.now(),
        "doc_name": doc_name
    }

def deactivate_doc(session_id: str, doc_id: str):
    """
    Called when user removes doc from active zone
    Clears cache for that doc immediately
    """
    if session_id in _active_docs:
        _active_docs[session_id].pop(doc_id, None)

    # Clear cached chunks for this doc
    clear_doc_cache(session_id, doc_id)

def get_active_doc_ids(session_id: str) -> list:
    """
    Returns list of currently active doc_ids for a session
    Used by rag_pipeline to filter chunks
    """
    if session_id not in _active_docs:
        return []

    return list(_active_docs[session_id].keys())

def get_active_docs(session_id: str) -> list:
    """
    Returns full active doc info for frontend
    """
    if session_id not in _active_docs:
        return []

    return [
        {
            "doc_id": doc_id,
            "doc_name": data["doc_name"],
            "activated_at": data["activated_at"].isoformat()
        }
        for doc_id, data in _active_docs[session_id].items()
    ]

def end_session(session_id: str):
    """
    Called when user closes the app or session expires
    Clears everything
    """
    _active_docs.pop(session_id, None)
    clear_session_cache(session_id)
    
def get_session_stats(session_id: str) -> dict:
    """
    Debug helper — shows active docs + cache stats together
    """
    return {
        "active_docs": get_active_docs(session_id),
        "cache_stats": get_cache_stats(session_id)
    }