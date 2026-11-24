# Hybrid router - Cloud + Local
# It demonstrates proficiency with the Strategy pattern & the ability to work 
# directly with the OpenAI SDK.

from openai import AsyncOpenAI
from app.core.config import settings
from app.schemas.incident import IncidentReport

class LLMRouter:
    def __init__(self):
        self.cloud_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.local_client = AsyncOpenAI(
            base_url=settings.OLLAMA_BASE_URL,
            api_key="ollama",
        )

    async def analyze_log(
        self, cleaned_log: str, runbook_name: str, runbook_context: str, mode: str = "mock") -> tuple[IncidentReport, dict]:
        # Quick mode without installing Ollama and without consuming RAM
        if mode == "mock":
            # Different diagnostic logic depending on the found procedure / log
            if "oomkilled" in cleaned_log.lower() or "137" in cleaned_log or "k8s" in runbook_name:
                report = IncidentReport(
                    severity="CRITICAL",
                    root_cause="Container killed by Linux OOM killer (Exit Code 137). Memory limit exceeded.",
                    cli_command="ssh admin@[REDACTED_IP_1] 'kubectl get pods -n prod | grep OOMKilled && kubectl top nodes'",
                    runbook_reference=runbook_name,
                )
            else:
                report = IncidentReport(
                    severity="HIGH",
                    root_cause="Upstream service refused connection (111: Connection refused). Backend worker pool down.",
                    cli_command="ssh admin@[REDACTED_IP_1] 'systemctl status app-backend && ss -tulpn | grep 8080'",
                    runbook_reference=runbook_name,
                )
            
            usage = {
                "prompt_tokens": 145,
                "completion_tokens": 58,
                "model_used": "on-prem-simulator",
                "mode": "mock",
            }
            return report, usage

        client = self.local_client if mode == "local" else self.cloud_client
        model = settings.LOCAL_MODEL_NAME if mode == "local" else settings.CLOUD_MODEL_NAME

        system_prompt = (
            "Ты — Senior NOC & DevOps инженер. Проанализируй лог ошибки по Runbook. "
            "Сохраняй плейсхолдеры вида [REDACTED_IP_1] без изменений в CLI-командах."
        )
        user_prompt = f"### RUNBOOK ({runbook_name}):\n{runbook_context}\n\n### ЛОГ:\n{cleaned_log}"

        response = await client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=IncidentReport,
            temperature=0.1,
        )

        report = response.choices[0].message.parsed
        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "model_used": model,
            "mode": mode,
        }
        return report, usage
