# Main API-pipeline

from fastapi import FastAPI
from pydantic import BaseModel
from app.services.scrubber import DataScrubber
from app.services.rag_engine import RAGEngine
from app.services.llm_router import LLMRouter
from app.services.finops_tracker import FinOpsTracker
from app.services.idempotency import IdempotencyGuard

app = FastAPI(title="Hybrid NOC & DevOps AI Assistant")

scrubber = DataScrubber()
rag = RAGEngine()
router = LLMRouter()
finops = FinOpsTracker()
idempotency = IdempotencyGuard()


class AnalyzeRequest(BaseModel):
    raw_log: str
    mode: str = "mock"  # "mock", "local" или "cloud"


class CreateTicketRequest(BaseModel):
    severity: str
    root_cause: str
    runbook_reference: str


@app.post("/analyze")
async def analyze_incident(req: AnalyzeRequest):
    # Masking Secrets and IP (for the CSP Security Co.)
    cleaned_log, mapping = scrubber.mask(req.raw_log)

    # Checking the Redis cache (for the FinOps Sela Co.)
    cached = await finops.get_cached_response(cleaned_log, req.mode)
    if cached:
        restored_cmd = scrubber.unmask(cached["report"]["cli_command"], mapping)
        cached["report"]["cli_command"] = restored_cmd
        cached["finops"]["cache_hit"] = True
        cached["finops"]["cost_usd"] = 0.0
        cached["security_preview"] = {"cleaned_log": cleaned_log, "masked_entities": len(mapping)}
        return cached

    # Searching for instructions in Qdrant (RAG)
    runbook_name, runbook_text = rag.search_runbook(cleaned_log)

    # Sending the cleaned log to the LLM
    report, usage = await router.analyze_log(cleaned_log, runbook_name, runbook_text, req.mode)
    cost = finops.calculate_cost(usage["prompt_tokens"], usage["completion_tokens"], req.mode)

    result_payload = {
        "report": report.model_dump(),
        "finops": {**usage, "cost_usd": cost, "cache_hit": False},
    }

    # Saving the scrubbed version in cache and restoring IP for the engineer
    await finops.save_response(cleaned_log, req.mode, result_payload)
    result_payload["report"]["cli_command"] = scrubber.unmask(report.cli_command, mapping)
    result_payload["security_preview"] = {"cleaned_log": cleaned_log, "masked_entities": len(mapping)}

    return result_payload


@app.post("/create-ticket")
async def create_ticket(req: CreateTicketRequest):
    return await idempotency.create_ticket_once(req.model_dump())
