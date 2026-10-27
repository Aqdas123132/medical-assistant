"""
cache_manager.py - Switch LangChain's LLM cache on and off.

LangChain checks the registered cache automatically before EVERY model call.
If the same prompt + same model settings were seen before, the stored answer
is returned instantly and no API call (no cost) is made.

Two cache types:
  - InMemoryCache : stored in RAM, fastest, lost when the app restarts.
  - SQLiteCache   : stored in a .db file on disk, survives restarts.
"""

from langchain_community.cache import SQLiteCache
from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache

from src.config import SQLITE_DB_PATH

# Streamlit re-runs app.py on every click. If we created a NEW InMemoryCache
# on each run, it would always be empty. So we create it ONCE here at module
# level; Python only imports this module once per server process.
_MEMORY_CACHE = InMemoryCache()


def configure_cache(mode: str) -> str:
    """
    Register the chosen cache globally.

    mode: "Off", "In-memory" or "SQLite"
    Returns a short text describing what is active (shown in the sidebar).
    """
    if mode == "In-memory":
        set_llm_cache(_MEMORY_CACHE)
        return "In-memory cache active (RAM, cleared on restart)."

    if mode == "SQLite":
        set_llm_cache(SQLiteCache(database_path=SQLITE_DB_PATH))
        return "SQLite cache active (file on disk, survives restart)."

    # "Off": passing None removes any cache.
    set_llm_cache(None)
    return "Cache is off - every request calls the API."


def clear_memory_cache() -> None:
    """Empty the in-memory cache (handy for demos and testing)."""
    _MEMORY_CACHE.clear()
