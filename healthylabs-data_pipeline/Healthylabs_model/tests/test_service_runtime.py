import asyncio

import pytest

pytest.importorskip("pydantic")

from healthylabs_inference.api.request_models import QueryRequest
from healthylabs_inference.core.config import Settings
from healthylabs_inference.service import QueryService


def test_sync_answer_rejects_running_event_loop():
    service = QueryService.from_settings(Settings(gemini_api_key="unused"))

    async def call_sync_answer():
        with pytest.raises(RuntimeError, match="Use answer_async"):
            service.answer(QueryRequest(query_text="What is pneumonia?"))

    asyncio.run(call_sync_answer())
    service.close()


class SlowService(QueryService):
    async def _run_pipeline(self, request):
        await asyncio.sleep(0.05)
        raise AssertionError("timeout should happen first")


def test_answer_async_enforces_timeout():
    settings = Settings(gemini_api_key="unused", request_timeout_seconds=0.001)
    service = SlowService.from_settings(settings)

    with pytest.raises(RuntimeError, match="Query exceeded"):
        asyncio.run(service.answer_async(QueryRequest(query_text="What is pneumonia?")))

    service.close()
