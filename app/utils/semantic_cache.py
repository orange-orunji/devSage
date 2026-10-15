import os
import hashlib
import numpy as np
from app.services.embedding_factory import get_embedding
from app.config.settings import get_settings
from app.utils.redis_client import get_redis


class SemanticCache:
    def __init__(self, similarity_threshold: float = 0.85, max_size: int = 200):
        self.threshold = similarity_threshold
        self.max_size = max_size
        self._embedding = get_embedding()
        self._question_vecs: list[np.ndarray] = []
        self._redis_keys: list[str] = []
        self._settings = get_settings()

    def _encode(self, text: str) -> np.ndarray:
        vec = self._embedding.embed_query(text)
        arr = np.array(vec, dtype=np.float32)
        arr = arr / np.linalg.norm(arr)
        return arr

    #  查缓存
    def lookup(self, question: str, user_id: str) -> str | None:
        if not self._question_vecs:
            return None

        redis_client = get_redis()
        if not redis_client:
            return None

        query_vec = self._encode(question)
        # 逐条计算余弦相似度，取最大值（不再用 np.vstack 全量矩阵）
        best_score = -1.0
        best_idx = -1
        user_prefix = (
            f"{self._settings.REDIS_USER_PREFIX}:semantic:{user_id}:"
        )

        for i, cached_vec in enumerate(self._question_vecs):
            if not self._redis_keys[i].startswith(user_prefix):
                continue

            score = float(np.dot(cached_vec, query_vec))
            if score > best_score:
                best_score = score
                best_idx = i

        if best_idx >= 0 and best_score >= self.threshold:
            key = self._redis_keys[best_idx]
            cached = redis_client.get(key)
            if cached:
                return cached
        return None

    # 存缓存
    def store(self, question: str, user_id: str, answer: str):
        redis_client = get_redis()
        if not redis_client:
            return

        qhash = hashlib.md5(question.encode()).hexdigest()[:12]
        key = f"{self._settings.REDIS_USER_PREFIX}:semantic:{user_id}:{qhash}"

        # LRU 淘汰：超过上限踢掉最老的
        if len(self._question_vecs) >= self.max_size:
            self._question_vecs.pop(0)
            self._redis_keys.pop(0)

        self._question_vecs.append(self._encode(question))
        self._redis_keys.append(key)

        redis_client.setex(name=key, value=answer, time=self._settings.REDIS_EXPIRE)


semantic_cache = SemanticCache()
