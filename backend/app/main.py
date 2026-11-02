from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.graph.workflow import run_discovery_workflow
from app.services.llm_service import check_llm_connection


app = FastAPI(
    title="NEXORA AI",
    description="Local-first Agentic Internship Intelligence Platform",
    version="0.1.0"
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
