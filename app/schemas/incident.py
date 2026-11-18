# incident.py file is the contract of responce/answer - Structured Output
# It should ensure that the LLM doesn`t return "fluff", 
# but instead provides strict JSON.

from typing import Literal
from pydantic import BaseModel, Field 

class IncidentReport(BaseModel):
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        description="Incident critically level")

    root_cause: str = Field(
        description="Brief technical reason for the failure, based on logs and documentation")

    cli_command: str = Field(
        description="Savety read-only CLI command for initial diagnostics"
    )

    runbook_reference: str = Field(
        description="Name of the policy document from the knowledge base, or 'Not found'"
    )