from typing import Literal

from pydantic import BaseModel, Field


class CandidateProfile(BaseModel):
    degrees: list[str] = Field(default_factory=list, max_length=20)
    branches: list[str] = Field(default_factory=list, max_length=20)
    academic_years: list[str] = Field(default_factory=list, max_length=10)
    cgpa: float | None = Field(default=None, ge=0, le=10)
    nationality: str | None = Field(default=None, max_length=100)
    target_domains: list[str] = Field(default_factory=list, max_length=20)
    preferred_locations: list[str] = Field(default_factory=list, max_length=20)


class DiscoveryRunRequest(BaseModel):
    user_request: str = Field(min_length=10, max_length=3000)
    candidate_profile: CandidateProfile | None = None
    max_results: int = Field(default=5, ge=1, le=10)


class EligibilityAssessment(BaseModel):
    status: Literal["eligible", "ineligible", "needs_review"]
    reasons: list[str] = Field(default_factory=list)
    evaluated_fields: list[str] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)


class RankingResult(BaseModel):
    score: float = Field(ge=0, le=100)
    factors: list[dict] = Field(default_factory=list)
    relevance_tags: list[str] = Field(default_factory=list)


ApplicationStatus = Literal[
    "interested",
    "preparing",
    "submitted",
    "interview",
    "offered",
    "accepted",
    "rejected",
    "withdrawn",
]


class CreateApplicationRequest(BaseModel):
    opportunity_id: str = Field(min_length=1, max_length=100)
    notes: str = Field(default="", max_length=4000)


class UpdateApplicationRequest(BaseModel):
    status: ApplicationStatus
    note: str = Field(default="", max_length=2000)
