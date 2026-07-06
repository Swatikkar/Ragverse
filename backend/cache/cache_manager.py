# backend/cache/cache_manager.py
from cache.cache_store import clear_doc_cache, clear_session_cache, get_cache_stats
from datetime import datetime

# Active docs structure:
# {
#   "{user_id}:{session_id}": {
#       doc_id: {
#           "activated_at": datetime,
#           "doc_name": str
#       }
#   }
# }

_active_docs: dict = {}


def _key(user_id: str, session_id: str) -> str:
    return f"{user_id}:{session_id}"


def activate_doc(session_id: str, doc_id: str, doc_name: str, user_id: str = None):
    cache_key = _key(user_id, session_id) if user_id else session_id
    if cache_key not in _active_docs:
        _active_docs[cache_key] = {}

    _active_docs[cache_key][doc_id] = {
        "activated_at": datetime.now(),
        "doc_name": doc_name
    }


def deactivate_doc(session_id: str, doc_id: str, user_id: str = None):
    cache_key = _key(user_id, session_id) if user_id else session_id
    if cache_key in _active_docs:
        _active_docs[cache_key].pop(doc_id, None)

    clear_doc_cache(session_id, doc_id, user_id)


def get_active_doc_ids(session_id: str, user_id: str = None) -> list:
    cache_key = _key(user_id, session_id) if user_id else session_id
    if cache_key not in _active_docs:
        return []
    return list(_active_docs[cache_key].keys())


def get_active_docs(session_id: str, user_id: str = None) -> list:
    cache_key = _key(user_id, session_id) if user_id else session_id
    if cache_key not in _active_docs:
        return []

    return [
        {
            "doc_id": doc_id,
            "doc_name": data["doc_name"],
            "activated_at": data["activated_at"].isoformat()
        }
        for doc_id, data in _active_docs[cache_key].items()
    ]


def end_session(session_id: str, user_id: str = None):
    cache_key = _key(user_id, session_id) if user_id else session_id
    _active_docs.pop(cache_key, None)
    clear_session_cache(session_id, user_id)


def get_session_stats(session_id: str, user_id: str = None) -> dict:
    return {
        "active_docs": get_active_docs(session_id, user_id),
        "cache_stats": get_cache_stats(session_id, user_id)
    }