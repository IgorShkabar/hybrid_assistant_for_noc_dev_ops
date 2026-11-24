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

        # Check if a ticket has already been created for this incident
        existing = await self.redis.get(key)
        if existing:
            data = json.loads(existing)
            data["duplicate_prevented"] = True
            return data

        # Atomic locking to prevent simultaneous parallel requests (Race Condition)
        lock_key = f"{key}:lock"
        acquired = await self.redis.set(lock_key, "1", nx=True, ex=15)
        if not acquired:
            return {
                "status": "in_progress",
                "message": "Ticket creation is already being processed",
                "duplicate_prevented": True,
            }

        try:
            # Simulation of calling external Jira / ServiceNow API (executed exactly once)
            ticket_id = f"NOC-{uuid.uuid4().hex[:6].upper()}"
            result = {
                "status": "created",
                "ticket_id": ticket_id,
                "severity": incident_payload.get("severity", "HIGH"),
                "summary": incident_payload.get("root_cause", ""),
                "duplicate_prevented": False,
            }

            # Save the result in Redis for 24 hours
            await self.redis.setex(key, 86400, json.dumps(result))
            return result
        finally:
            await self.redis.delete(lock_key)
