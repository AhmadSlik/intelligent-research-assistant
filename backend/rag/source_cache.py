import hashlib
import json
import logging
import time

from rag.rag_engine import client, model

logger = logging.getLogger(__name__)

CACHE_COLLECTION = "cached_sources"
TTL_SECONDS = 7 * 24 * 3600

_collection = client.get_or_create_collection(CACHE_COLLECTION)
_PLACEHOLDER_EMBEDDING = model.encode("source_cache_entry").tolist()


def _make_key(topic: str, lang: str) -> str:
    from utils.arabic import normalize_for_search
    normalized = normalize_for_search(topic)
    raw = f"{normalized}|{lang}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached_sources(topic: str, lang: str) -> list[dict] | None:
    key = _make_key(topic, lang)
    try:
        result = _collection.get(ids=[key])
    except Exception as e:
        logger.warning("Cache GET failed: %s", e)
        return None

    if not result["ids"]:
        return None

    meta = result["metadatas"][0] or {}
    cached_at = int(meta.get("cached_at", 0))
    if (time.time() - cached_at) > TTL_SECONDS:
        logger.info("Cache entry expired for key=%s", key[:8])
        try:
            _collection.delete(ids=[key])
        except Exception:
            pass
        return None

    try:
        return json.loads(meta.get("sources_json", "[]"))
    except Exception:
        return None


def set_cached_sources(topic: str, lang: str, sources: list[dict]) -> None:
    key = _make_key(topic, lang)
    payload = {
        "cached_at": int(time.time()),
        "sources_json": json.dumps(sources, ensure_ascii=False),
        "topic": topic,
        "lang": lang,
    }
    try:
        _collection.upsert(
            ids=[key],
            embeddings=[_PLACEHOLDER_EMBEDDING],
            documents=[f"cache:{topic}:{lang}"],
            metadatas=[payload],
        )
    except Exception as e:
        logger.warning("Cache SET failed: %s", e)
