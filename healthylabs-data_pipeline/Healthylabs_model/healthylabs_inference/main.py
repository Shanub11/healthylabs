"""Standalone FastAPI app entrypoint for local inference development."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from healthylabs_inference.api.routes import SERVICE_STATE_KEY
from healthylabs_inference.api.routes import router as query_router
from healthylabs_inference.service import QueryService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    service = QueryService.from_settings()
    await asyncio.to_thread(service.direct_strategy.retriever.embedder.embed_query, "warmup")
    setattr(app.state, SERVICE_STATE_KEY, service)
    try:
        yield
    finally:
        service.close()


app = FastAPI(title="HealthyLabs Inference", version="0.1.0", lifespan=lifespan)
app.include_router(query_router)
