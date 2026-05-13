import pytest

pytest.importorskip("pydantic")

from healthylabs_inference.api.request_models import QueryRequest
from healthylabs_inference.core.config import Settings
from healthylabs_inference.retrieval.strategies.visual import VisualResult
from healthylabs_inference.synthesis.response_builder import ResponseBuilder


class CapturingMultimodalLLM:
    def __init__(self):
        self.prompt = ""
        self.images = []

    def generate(self, prompt, **kwargs):
        raise AssertionError("multimodal generation should be used when images are present")

    def generate_multimodal(self, prompt, *, image_bytes_list=None, **kwargs):
        self.prompt = prompt
        self.images = image_bytes_list or []
        return type("Response", (), {"text": "multimodal answer"})()


class EmptyCitationClient:
    def fetch_citations(self, doc_uids):
        return {}


def test_response_builder_adds_visual_evidence_and_frontend_assets():
    llm = CapturingMultimodalLLM()
    builder = ResponseBuilder(llm, EmptyCitationClient(), Settings())

    built = builder.build(
        request=QueryRequest(query_text="What does this diagram show?"),
        chunks=[],
        contradictions_found=False,
        safety_flags=[],
        visual_results=[
            VisualResult(
                storage_path="s3://bucket/image.png",
                caption="Medication dosing table",
                doc_uid="doc-visual",
                score=0.87,
                image_bytes=b"\x89PNG\r\n\x1a\nimage",
                presigned_url="https://signed/image.png",
            )
        ],
    )

    assert built.answer == "multimodal answer"
    assert llm.images == [b"\x89PNG\r\n\x1a\nimage"]
    assert "Medication dosing table" in llm.prompt
    assert built.visual_assets[0].url == "https://signed/image.png"
    assert built.visual_assets[0].alt_text == "Medication dosing table"
    assert built.visual_assets[0].source_document == "doc-visual"
