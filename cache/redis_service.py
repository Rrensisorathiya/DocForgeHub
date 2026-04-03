"""
Redis Cache Service — Project 2 RAG
Handles: retrieval cache + session context + Notion rate limiting
"""

import json
import hashlib
import time
from typing import Optional, Any
from utils.logger import setup_logger

logger = setup_logger(__name__)

try:
    import redis
    _redis_available = True
except ImportError:
    _redis_available = False
    logger.warning("redis-py not installed. Run: pip install redis")

TTL_RETRIEVAL = 3600
TTL_SESSION   = 1800
TTL_NOTION    = 300
TTL_EMBEDDING = 86400


class RedisService:
    def __init__(self, url: str = "redis://localhost:6379", db: int = 0):
        self._client = None
        self._url    = url
        if _redis_available:
            try:
                self._client = redis.Redis.from_url(
                    url, db=db, decode_responses=True,
                    socket_connect_timeout=3,
                )
                self._client.ping()
                logger.info(f"Redis connected: {url}")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e} — running without cache")
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def _safe(self, func, *args, **kwargs):
        if not self._client:
            return None
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Redis op failed: {e}")
            return None

    @staticmethod
    def _retrieval_key(query: str, filters: dict) -> str:
        raw = f"{query}|{json.dumps(filters, sort_keys=True)}"
        return f"retrieval:{hashlib.md5(raw.encode()).hexdigest()}"

    @staticmethod
    def _session_key(session_id: str) -> str:
        return f"session:{session_id}"

    @staticmethod
    def _embedding_key(text: str) -> str:
        return f"embedding:{hashlib.md5(text.encode()).hexdigest()}"

    @staticmethod
    def _notion_rate_key(database_id: str) -> str:
        window = int(time.time() // 60)
        return f"notion_rate:{database_id}:{window}"

    def get_retrieval(self, query: str, filters: dict) -> Optional[list]:
        key  = self._retrieval_key(query, filters)
        data = self._safe(self._client.get, key)
        if data:
            logger.debug(f"Cache HIT: retrieval")
            return json.loads(data)
        return None

    def set_retrieval(self, query: str, filters: dict, results: list) -> None:
        key = self._retrieval_key(query, filters)
        self._safe(self._client.setex, key, TTL_RETRIEVAL, json.dumps(results))

    def get_session(self, session_id: str) -> list:
        key  = self._session_key(session_id)
        data = self._safe(self._client.get, key)
        return json.loads(data) if data else []

    def append_session(self, session_id: str, role: str, content: str) -> None:
        key     = self._session_key(session_id)
        history = self.get_session(session_id)
        history.append({"role": role, "content": content})
        history = history[-20:]
        self._safe(self._client.setex, key, TTL_SESSION, json.dumps(history))

    def clear_session(self, session_id: str) -> None:
        key = self._session_key(session_id)
        self._safe(self._client.delete, key)
        logger.info(f"Session cleared: {session_id}")

    def get_embedding(self, text: str) -> Optional[list]:
        key  = self._embedding_key(text)
        data = self._safe(self._client.get, key)
        return json.loads(data) if data else None

    def set_embedding(self, text: str, vector: list) -> None:
        key = self._embedding_key(text)
        self._safe(self._client.setex, key, TTL_EMBEDDING, json.dumps(vector))

    def check_notion_rate(self, database_id: str, limit: int = 90) -> bool:
        key   = self._notion_rate_key(database_id)
        count = self._safe(self._client.incr, key)
        if count == 1:
            self._safe(self._client.expire, key, 60)
        if count and count > limit:
            logger.warning(f"Notion rate limit hit: {count} req/min")
            return False
        return True

    def get_notion_rate_count(self, database_id: str) -> int:
        key   = self._notion_rate_key(database_id)
        count = self._safe(self._client.get, key)
        return int(count) if count else 0

    def get(self, key: str) -> Optional[Any]:
        data = self._safe(self._client.get, key)
        return json.loads(data) if data else None

    def set(self, key: str, value: Any, ttl: int = TTL_RETRIEVAL) -> None:
        self._safe(self._client.setex, key, ttl, json.dumps(value))

    def delete(self, key: str) -> None:
        self._safe(self._client.delete, key)

    def flush_all(self) -> None:
        self._safe(self._client.flushdb)
        logger.warning("Redis cache flushed!")

    def stats(self) -> dict:
        if not self._client:
            return {"available": False}
        try:
            info = self._client.info()
            keys = self._client.dbsize()
            return {
                "available":   True,
                "total_keys":  keys,
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected":   info.get("connected_clients", 0),
                "hits":        info.get("keyspace_hits", 0),
                "misses":      info.get("keyspace_misses", 0),
            }
        except Exception as e:
            return {"available": False, "error": str(e)}


import os
from dotenv import load_dotenv
load_dotenv()

redis_client = RedisService(
    url=os.getenv("REDIS_URL", "redis://localhost:6379")
)