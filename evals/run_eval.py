# Auto-testing script
# This script checks three critical aspects at once: 
# that DataScrubber hasn’t missed any secrets, 
# that the RAG system has retrieved the correct document, 
# and that the Pydantic schema remains intact.

import asyncio
import json
import sys
import os

# Добавляем корень проекта в PYTHONPATH для корректного импорта app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.scrubber import DataScrubber
from app.services.rag_engine import RAGEngine
from app.services.llm_router import LLMRouter


async def run_evaluations():
    with open("evals/test_cases.json", "r", encoding="utf-8") as f:
        cases = json.load(f)

    scrubber = DataScrubber()
    rag = RAGEngine()
    router = LLMRouter()

    passed = 0
    total = len(cases)

    print(f"Running {total} evaluation test cases...\n")

    for case in cases:
        case_id = case["id"]
        raw_log = case["raw_log"]

        # 1. Тест безопасности (Scrubber)
        cleaned_log, mapping = scrubber.mask(raw_log)
        leaked = [item for item in case["must_mask"] if item in cleaned_log]
        if leaked:
            print(f"❌ [{case_id}] SECURITY FAIL: Leaked entities -> {leaked}")
            continue

        # 2. Тест поиска документации (RAG)
        runbook_name, runbook_text = rag.search_runbook(cleaned_log)
        if runbook_name != case["expected_runbook"]:
            print(f"❌ [{case_id}] RAG FAIL: Expected {case['expected_runbook']}, got {runbook_name}")
            continue

        # 3. Тест контракта ответа (LLM Structured Output)
        report, _ = await router.analyze_log(cleaned_log, runbook_name, runbook_text, mode="mock")
        if report.severity != case["expected_severity"]:
            print(f"❌ [{case_id}] LLM FAIL: Expected severity {case['expected_severity']}, got {report.severity}")
            continue

        print(f"✅ [{case_id}] PASSED (Masked {len(mapping)} entities | Runbook: {runbook_name})")
        passed += 1

    print(f"\n📊 Evaluation Summary: {passed}/{total} passed ({(passed/total)*100:.0f}%)")
    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_evaluations())

# Как запустить и проверить (1 команда в терминале): 
# Убедись, что Docker (Qdrant) запущен и активирован (venv):  docker compose up -d     docker ps
# вбей в VS Code Terminal:      python3 evals/run_eval.py
 
