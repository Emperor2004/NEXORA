from fastapi import FastAPI, HTTPException
import hmac
import ipaddress
import logging
import os

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

from app.graph.workflow import run_discovery_workflow, run_supervised_workflow
from app.services.llm_service import check_llm_connection
from app.schemas.workflow import (
    CreateApplicationRequest,
    DiscoveryRunRequest,
    UpdateApplicationRequest,
)
from app.services.internship_workflow_service import InternshipWorkflow
from app.services.opportunity_store import LocalOpportunityStore


logger = logging.getLogger("nexora.api")


app = FastAPI(
    title="NEXORA AI",
    description="Local-first Agentic Internship Intelligence Platform",
    version="0.1.0"
)


@app.middleware("http")
async def protect_api_routes(request: Request, call_next):
    if not request.url.path.startswith("/api/"):
        return await call_next(request)

    configured_token = os.getenv("NEXORA_API_TOKEN", "").strip()
    if configured_token:
        scheme, _, supplied_token = request.headers.get(
            "authorization", ""
        ).partition(" ")
        if (
            scheme.casefold() != "bearer"
            or not hmac.compare_digest(supplied_token.strip(), configured_token)
        ):
            return JSONResponse(
                {"detail": "A valid bearer token is required."},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
    else:
        client_host = request.client.host if request.client else ""
        try:
            loopback = ipaddress.ip_address(client_host).is_loopback
        except ValueError:
            loopback = False
        if not loopback:
            return JSONResponse(
                {"detail": "API access is restricted to loopback without NEXORA_API_TOKEN."},
                status_code=403,
            )

    return await call_next(request)


configured_cors_origins = os.getenv(
    "NEXORA_CORS_ORIGINS",
    "http://127.0.0.1:5173,http://localhost:5173",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in configured_cors_origins.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class DiscoveryRequest(BaseModel):

    user_request: str = Field(
        min_length=10,
        max_length=3000
    )


@app.get("/")
def root():

    return {
        "application": "NEXORA AI",
        "status": "running",
        "version": "0.1.0"
    }


@app.get("/health")
def health():

    return {"status": "healthy"}


@app.get("/health/ollama")
def ollama_health():

    result = check_llm_connection()

    if not result["connected"]:
        raise HTTPException(status_code=503, detail=result)

    return result


@app.post("/api/discovery/plan")
def discovery_plan(request: DiscoveryRequest):

    try:

        result = run_discovery_workflow(
            request.user_request
        )

        if result.get("error"):
            raise HTTPException(
                status_code=500,
                detail=result["error"]
            )

        return {
            "agent": "NEXORA Discovery Agent",
            "status": "completed",
            "plan": result["plan"]
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@app.post("/api/workflow/run")
def run_internship_workflow(request: DiscoveryRunRequest):
    try:
        profile = (
            request.candidate_profile.model_dump()
            if request.candidate_profile
            else None
        )
        return run_supervised_workflow(
            user_request=request.user_request,
            candidate_profile=profile,
            max_results=request.max_results,
            workflow_runner=InternshipWorkflow().run,
        )
    except Exception as error:
        logger.exception("Discovery workflow failed")
        raise HTTPException(
            status_code=502,
            detail="Discovery workflow failed. Check server logs for details.",
        ) from error


@app.get("/api/opportunities")
def list_opportunities(limit: int = 50, offset: int = 0):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(status_code=422, detail="Invalid pagination values")
    return {
        "opportunities": LocalOpportunityStore().list_opportunities(limit, offset),
        "limit": limit,
        "offset": offset,
    }


@app.get("/api/opportunities/{opportunity_id}")
def get_opportunity(opportunity_id: str):
    opportunity = LocalOpportunityStore().get_opportunity(opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opportunity


@app.get("/api/opportunities/{opportunity_id}/application-checklist")
def application_checklist(opportunity_id: str):
    opportunity = LocalOpportunityStore().get_opportunity(opportunity_id)
    if opportunity is None:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    extraction = opportunity.get("extraction", {})
    return {
        "opportunity_id": opportunity_id,
        "application_url": extraction.get("application_url"),
        "vacancy_source_url": opportunity.get("source", {}).get("url"),
        "application_url_confirmed": bool(extraction.get("application_url")),
        "source_stated_application_method": extraction.get("application_method"),
        "source_stated_eligibility": extraction.get("eligibility_summary"),
        "eligibility_status": opportunity.get("eligibility", {}).get(
            "status", "needs_review"
        ),
        "recommended_user_checks": [
            "Confirm the vacancy is still open on the source page.",
            "Review eligibility and application instructions before submitting.",
            "Prepare your resume and any materials requested by the employer.",
        ],
        "automated_submission": False,
    }


@app.get("/api/applications")
def list_applications(limit: int = 50, offset: int = 0):
    if not 1 <= limit <= 100 or offset < 0:
        raise HTTPException(status_code=422, detail="Invalid pagination values")
    return {
        "applications": LocalOpportunityStore().list_applications(limit, offset),
        "limit": limit,
        "offset": offset,
    }


@app.post("/api/applications", status_code=201)
def create_application(request: CreateApplicationRequest):
    try:
        return LocalOpportunityStore().create_application(
            request.opportunity_id, request.notes
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.patch("/api/applications/{application_id}")
def update_application(application_id: str, request: UpdateApplicationRequest):
    try:
        return LocalOpportunityStore().update_application(
            application_id, request.status, request.note
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
