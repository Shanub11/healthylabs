import sys
import types
from types import SimpleNamespace

import pytest

from healthylabs_inference.core.config import Settings
from healthylabs_inference.core.llm_client import GeminiClient


class FlakyModels:
    def __init__(self):
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary 503")
        return SimpleNamespace(text="ok")


class FakeClient:
    def __init__(self):
        self.models = FlakyModels()


class FakeGenerateContentConfig:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakePart:
    @classmethod
    def from_text(cls, *, text):
        return {"type": "text", "text": text}

    @classmethod
    def from_bytes(cls, *, data, mime_type):
        return {"type": "bytes", "data": data, "mime_type": mime_type}


@pytest.fixture(autouse=True)
def fake_google_genai(monkeypatch):
    google = types.ModuleType("google")
    genai = types.ModuleType("google.genai")
    genai_types = types.ModuleType("google.genai.types")
    genai_types.GenerateContentConfig = FakeGenerateContentConfig
    genai_types.Part = FakePart
    genai.types = genai_types
    google.genai = genai
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.genai", genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", genai_types)


def test_gemini_generate_retries_transient_failure(monkeypatch):
    client = GeminiClient(Settings(gemini_api_key="key"))
    fake = FakeClient()
    monkeypatch.setattr(client, "_get_client", lambda: fake)
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    response = client.generate("hello", retries=1)

    assert response.text == "ok"
    assert fake.models.calls == 2


def test_gemini_generate_raises_after_retries(monkeypatch):
    client = GeminiClient(Settings(gemini_api_key="key"))
    fake = FakeClient()
    monkeypatch.setattr(client, "_get_client", lambda: fake)
    monkeypatch.setattr("time.sleep", lambda seconds: None)

    with pytest.raises(RuntimeError, match="Gemini failed after 1 attempts"):
        client.generate("hello", retries=0)



def test_gemini_generate_multimodal_uses_bytes_parts(monkeypatch):
    client = GeminiClient(Settings(gemini_api_key="key"))
    fake = FakeClient()
    monkeypatch.setattr(client, "_get_client", lambda: fake)

    response = client.generate_multimodal(
        "look at this", image_bytes_list=[b"\x89PNG\r\n\x1a\nimage"], retries=1
    )

    assert response.text == "ok"
    assert fake.models.calls == 2
