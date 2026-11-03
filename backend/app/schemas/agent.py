"""Validated contracts shared by NEXORA workflow agents."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.workflow import CandidateProfile


AgentStatus = Literal[
    "pending", "running", "succeeded", "partial", "needs_review",
    "retryable_failure", "terminal_failure", "skipped",
]
PrivacyClassification = Literal[
    "public", "public_source_content", "user_provided", "candidate_profile", "sensitive",
]


class AgentTaskEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str = Field(min_length=1, max_length=100)
    task_id: str = Field(min_length=1, max_length=100)
    parent_task_id: str | None = Field(default=None, max_length=100)
    agent_name: str = Field(min_length=1, max_length=100)
    agent_version: str = Field(min_length=1, max_length=40)
    input_schema_version: str = Field(default="1", max_length=40)
    input_reference_ids: list[str] = Field(default_factory=list, max_length=100)
    deadline: datetime
    retry_count: int = Field(default=0, ge=0, le=5)
    privacy_classification: PrivacyClassification = "public"
    requested_output_schema: str = Field(min_length=1, max_length=200)
    input_payload: dict[str, Any] = Field(default_factory=dict, exclude=True)

    @field_validator("deadline")
    @classmethod
    def require_timezone_aware_deadline(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Agent task deadlines must include a timezone")
        return value


class AgentResultEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    task_id: str
    agent_name: str
    agent_version: str
    status: AgentStatus
    structured_output: dict[str, Any] = Field(default_factory=dict)
    evidence_reference_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence_or_uncertainty: str | None = None
    tool_trace: list[dict[str, Any]] = Field(default_factory=list)
    model_provider: str | None = None
    model_name: str | None = None
    token_and_cost_metadata: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    completed_at: datetime


class AgentProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    version: str
    lifecycle: Literal["integrated", "planned"]
    mission: str
    system_instructions: str
    input_schema: str
    output_schema: str
    tool_permissions: tuple[str, ...] = ()
    shared_state_reads: tuple[str, ...] = ()
    shared_state_writes: tuple[str, ...] = ()
    decision_policy: tuple[str, ...] = ()
    model_profile: str
    allowed_providers: tuple[str, ...] = ()
    max_output_tokens: int | None = Field(default=1024, ge=1, le=32768)
    timeout_seconds: int = Field(default=90, ge=1, le=3600)
    max_retries: int = Field(default=0, ge=0, le=5)
    privacy_classification: PrivacyClassification = "public"


class DiscoveryPlannerInput(BaseModel):
    user_request: str = Field(min_length=10, max_length=3000)


class OpportunityExtractorInput(BaseModel):
    source_text: str = Field(min_length=1, max_length=100_000)
    source_url: str = Field(min_length=1, max_length=2048)
    source_title: str = Field(default="", max_length=500)
    source_type: str = Field(default="unknown", max_length=100)
    candidate_metadata: dict[str, Any] | None = None


class WorkflowSupervisorInput(BaseModel):
    user_request: str = Field(min_length=10, max_length=3000)
    candidate_profile: CandidateProfile | None = None
    max_results: int = Field(default=5, ge=1, le=10)
