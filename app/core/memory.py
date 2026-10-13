import logging
from functools import lru_cache
from mem0 import MemoryClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)

@lru_cache
def get_memory_client():
    api_key = get_settings().mem0_api_key

    if not api_key:
        logger.warning("MEM0_API_KEY not set - long-term memory disabled");
        return None
    return MemoryClient(api_key=api_key)

# searcing a qiery in memorie
def search_memories(query: str, user_id: str, limit: int = 5) -> list[str]:
    client = get_memory_client()
    if client is None:
        return []

    try:
        res = client.search(
            query,
            filters={"user_id": user_id},
            limit=limit,
        )
        items = res.get("results", []) if isinstance(res, dict) else res

        return [m["memory"] for m in items]
    except Exception:
        logger.exception("Mem0 search failed")
        return []

# save the data in memory
def save_memory(quesions: str, answer: str, user_id: str) -> None:
    client = get_memory_client()

    if client is None:
        return

    try:
        client.add(
            [
                {
                    "role": "user",
                    "content": quesions,
                },
                {
                    "role": "assistant",
                    "content": answer,
                }
            ],
            user_id=user_id
        )

    except Exception:
        logger.exception("Mem0 add failed")
    