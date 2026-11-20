# Decorator/wrapper

import json
import hashlib
import uuid
import redis.asyncio as redis
from app.core.config import settings


class IdempotencyGuard:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

    def build_key(self, action_name: str, payload: dict) -> str:
        raw = f"{action_name}:{json.dumps(payload, sort_keys=True)}"
        digest = hashlib.sha256(raw.encode()).hexdigest()
        return f"idemp:{action_name}:{digest}"

    async def create_ticket_once(self, incident_payload: dict) -> dict:
        key = self.build_key("create_ticket", incident_payload)

        # 1. Проверяем, не создавался ли уже тикет по этому инциденту
        existing = await self.redis.get(key)
        if existing:
            data = json.loads(existing)
            data["duplicate_prevented"] = True
            return data

        # 2. Атомарная блокировка от одновременных параллельных запросов (Race Condition)
        lock_key = f"{key}:lock"
        acquired = await self.redis.set(lock_key, "1", nx=True, ex=15)
        if not acquired:
            return {
                "status": "in_progress",
                "message": "Ticket creation is already being processed",
                "duplicate_prevented": True,
            }

        try:
            # 3. Симуляция вызова внешнего Jira / ServiceNow API (выполняется строго 1 раз)
            ticket_id = f"NOC-{uuid.uuid4().hex[:6].upper()}"
            result = {
                "status": "created",
                "ticket_id": ticket_id,
                "severity": incident_payload.get("severity", "HIGH"),
                "summary": incident_payload.get("root_cause", ""),
                "duplicate_prevented": False,
            }

            # 4. Сохраняем результат в Redis на 24 часа
            await self.redis.setex(key, 86400, json.dumps(result))
            return result
        finally:
            await self.redis.delete(lock_key)
