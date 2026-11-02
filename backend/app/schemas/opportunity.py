from typing import Literal

from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    field_name: str = Field(
        description="Exact field supported by this evidence."
    )
    source_location: str = Field(
        description="Heading, HTML section, or PDF page number."
    )
    quote: str = Field(
        description="Verbatim quotation copied from the extracted source text."
    )


class OpportunityExtraction(BaseModel):
    document_kind: Literal[
        "individual_announcement",
        "listing_page",
        "programme_information",
        "institutional_portal",
        "unknown"
    ] = Field(
        description="What kind of source document this is."
    )

    opportunity_title: str | None = None
    organization: str | None = None

    location: str | None = None
    work_mode: str | None = None
    employment_type: str | None = None

    research_areas: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)

    is_paid: bool | None = None
    stipend: str | None = None
    duration: str | None = None
    posting_age: str | None = None

    start_date: str | None = None
    end_date: str | None = None
    application_deadline: str | None = None

    eligible_degrees: list[str] = Field(default_factory=list)
    eligible_branches: list[str] = Field(default_factory=list)
    eligible_years: list[str] = Field(default_factory=list)

    minimum_cgpa: str | None = None
    nationality_requirement: str | None = None
    eligibility_summary: str | None = None

    application_method: str | None = None
    application_url: str | None = None
    contact_email: str | None = None

    extraction_notes: list[str] = Field(default_factory=list)

    evidence: list[EvidenceItem] = Field(default_factory=list)
