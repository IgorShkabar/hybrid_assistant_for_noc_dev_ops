# FinOps-tracker and Redis-cache 

import json
import hashlib
import redis.asyncio as redis
from app.core.config import settings


class FinOpsTracker:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        # Approximate price per 1M tokens (gpt-4o-mini)
        self.input_price_per_1m = 0.15
        self.output_price_per_1m = 0.60

    def _make_key(self, cleaned_log: str, mode: str) -> str:
        digest = hashlib.sha256(f"{mode}:{cleaned_log}".encode()).hexdigest()
        return f"noc_cache:{digest}"

    async def get_cached_response(self, cleaned_log: str, mode: str) -> dict | None:
        data = await self.redis.get(self._make_key(cleaned_log, mode))
        return json.loads(data) if data else None

    async def save_response(self, cleaned_log: str, mode: str, payload: dict):
        # We save the cache for 1 hour (3600 seconds)
        await self.redis.setex(self._make_key(cleaned_log, mode), 3600, json.dumps(payload))

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int, mode: str) -> float:
        if mode in ("local", "mock"):
            return 0.0  # Local environment does not consume cloud budget
        cost = (prompt_tokens / 1_000_000) * self.input_price_per_1m + (
            completion_tokens / 1_000_000
        ) * self.output_price_per_1m
        return round(cost, 6)
