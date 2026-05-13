"""FastAPI routes for the HealthyLabs model/retrieval layer."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from healthylabs_inference.api.request_models import QueryRequest, QueryResponse
from healthylabs_inference.service import QueryService

router = APIRouter(tags=["healthylabs-query"])

SERVICE_STATE_KEY = "healthylabs_query_service"


def get_query_service(request: Request) -> QueryService:
    """Return the startup-initialized app-scoped QueryService."""

    service = getattr(request.app.state, SERVICE_STATE_KEY, None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="HealthyLabs query service is not initialized; configure FastAPI lifespan startup.",
        )
    return service


@router.post("/refinery/v1/query", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def query_refinery(payload: QueryRequest, request: Request) -> QueryResponse:
    """Answer a medical question using BioLORD embeddings, Neo4j RAG, and Gemini synthesis."""

    service = get_query_service(request)
    try:
        return await service.answer_async(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
