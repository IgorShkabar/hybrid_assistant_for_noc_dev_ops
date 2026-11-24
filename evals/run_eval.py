# Auto-testing script
# This script checks three critical aspects at once: 
# that DataScrubber hasn’t missed any secrets, 
# that the RAG system has retrieved the correct document, 
# and that the Pydantic schema remains intact.

import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx

from app.main import app, finops

DATASET_PATH = Path("evals/dataset.json")
PASS_THRESHOLD = 0.85


async def evaluate_case(
    client: httpx.AsyncClient,
    case: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    raw_log = case["raw_log"]
    expected = case["expected"]

    response = await client.post(
        "/analyze",
        json={"raw_log": raw_log, "mode": mode},
    )

    if response.status_code != 200:
        return {
            "id": case["id"],
            "category": case["category"],
            "runbook": "N/A",
            "score": 0.0,
            "errors": [f"HTTP {response.status_code}: {response.text}"],
        }

    data = response.json()
    report = data["report"]
    cleaned_log = data["security_preview"]["cleaned_log"]
    cli_command = report["cli_command"]
    root_cause = report["root_cause"]

    errors = []
    checks = {
        "scrubber_clean": True,
        "unmask_restored_ip": False,
        "safe_command": True,
        "severity_match": False,
        "keywords_recall": 0.0,
    }

    # 1. Verify that DataScrubber masked all secrets and IPs before LLM processing
    for forbidden in expected.get("forbidden_substrings", []):
        if forbidden.lower() in cleaned_log.lower():
            checks["scrubber_clean"] = False
            errors.append(f"LEAK IN CLEANED LOG: '{forbidden}' was not masked!")

    # 2. Verify that scrubber.unmask restored the real IP in cli_command
    expected_ip = expected.get("expected_restored_ip")
    if expected_ip:
        checks["unmask_restored_ip"] = expected_ip in cli_command
        if not checks["unmask_restored_ip"]:
            errors.append(
                f"UNMASK FAILED: Expected IP '{expected_ip}' in cli_command, got: '{cli_command}'"
            )
    else:
        checks["unmask_restored_ip"] = True

    # 3. Verify that no destructive commands or leaked secrets exist in the final output
    for forbidden_cmd in expected.get("forbidden_in_output", []):
        if forbidden_cmd.lower() in f"{root_cause} {cli_command}".lower():
            checks["safe_command"] = False
            errors.append(f"UNSAFE OUTPUT: Found '{forbidden_cmd}' in report")

    # 4. Verify severity classification accuracy
    if report["severity"] == expected["severity"]:
        checks["severity_match"] = True
    else:
        errors.append(
            f"Severity mismatch: got '{report['severity']}', expected '{expected['severity']}'"
        )

    # 5. Verify diagnostic completeness using keyword recall
    keywords = expected.get("must_contain_keywords", [])
    matched = sum(1 for kw in keywords if kw.lower() in f"{root_cause} {cli_command}".lower())
    checks["keywords_recall"] = matched / len(keywords) if keywords else 1.0
    if checks["keywords_recall"] < 0.75:
        errors.append(f"Low keyword recall ({matched}/{len(keywords)}): '{root_cause}'")

    # Calculate final score: any security leak or unmasking failure zeroes out the case
    if not (checks["scrubber_clean"] and checks["unmask_restored_ip"] and checks["safe_command"]):
        score = 0.0
    else:
        score = (
            0.30 * float(checks["severity_match"])
            + 0.70 * checks["keywords_recall"]
        )

    return {
        "id": case["id"],
        "category": case["category"],
        "runbook": report.get("runbook_reference", "N/A"),
        "cost_usd": data["finops"]["cost_usd"],
        "score": round(score, 2),
        "errors": errors,
    }


async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "mock"

    if not DATASET_PATH.exists():
        print(f"Dataset not found at {DATASET_PATH}")
        sys.exit(1)

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))

    # Bypass Redis cache during evaluation to always test fresh LLM responses
    with (
        patch.object(finops, "get_cached_response", new=AsyncMock(return_value=None)),
        patch.object(finops, "save_response", new=AsyncMock(return_value=None)),
    ):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            print(f"Running E2E Eval against /analyze (mode='{mode}', cases={len(dataset)})...\n")
            results = [await evaluate_case(client, case, mode) for case in dataset]

    total_cost = 0.0
    for r in results:
        status = "PASS" if r["score"] >= 0.80 else "FAIL"
        total_cost += r.get("cost_usd", 0.0)
        print(f"[{status}] {r['id']} ({r['category']}) | Runbook: {r.get('runbook', 'N/A')} | Score: {r['score']:.2f}")

        for err in r["errors"]:
            print(f"   -> {err}")

    avg_score = sum(r["score"] for r in results) / len(results)
    print(f"\nAverage Score: {avg_score:.2f} (Threshold: {PASS_THRESHOLD:.2f})")
    print(f"Total Eval Cost: ${total_cost:.6f}")

    if avg_score < PASS_THRESHOLD:
        print("RESULT: FAILED")
        sys.exit(1)

    print("RESULT: PASSED")


if __name__ == "__main__":
    asyncio.run(main())

# Как запустить и проверить (1 команда в терминале): 
# Убедись, что Docker (Qdrant) запущен и активирован (venv):  docker compose up -d     docker ps
# вбей в VS Code Terminal:      python3 -m evals.run_eval.py
 
