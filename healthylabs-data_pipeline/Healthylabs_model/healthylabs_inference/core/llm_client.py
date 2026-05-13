"""Gemini LLM client used by routing, HYDE, and answer synthesis."""

from __future__ import annotations

import json
import time
from io import BytesIO
from dataclasses import dataclass
from typing import Any

from healthylabs_inference.core.config import Settings

@dataclass(frozen=True, slots=True)
class LLMResponse:
    text: str
    raw: Any | None = None


class GeminiClient:
    """Provider-aware LLM wrapper with helpers for strict JSON prompts.

    The historical class name is kept so the existing RAG orchestration and
    tests do not need a broad refactor. If ``LLM_PROVIDER`` is unset, Gemini is
    used when ``GEMINI_API_KEY`` exists; otherwise the Hugging Face MedGemma
    model configured by ``HF_MODEL_NAME`` is used with ``HF_TOKEN``.
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client = None
        self._hf_tokenizer = None
        self._hf_processor = None
        self._hf_model = None

    @property
    def provider(self) -> str:
        configured = self._settings.llm_provider.strip().lower()
        if configured:
            return configured
        if self._settings.hf_token:
            return "huggingface"
        if self._settings.gemini_api_key:
            return "gemini"
        return "huggingface"

    def _get_client(self):
        if not self._settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required for Gemini generation.")
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._settings.gemini_api_key)
        return self._client

    def _get_hf_components(self):
        if not self._settings.hf_token:
            raise RuntimeError("HF_TOKEN is required for Hugging Face MedGemma generation.")
        if self._hf_model is None or self._hf_tokenizer is None:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            dtype = _resolve_torch_dtype(torch, self._settings.hf_torch_dtype)
            self._hf_tokenizer = AutoTokenizer.from_pretrained(
                self._settings.hf_model_name,
                token=self._settings.hf_token,
            )
            self._hf_model = AutoModelForCausalLM.from_pretrained(
                self._settings.hf_model_name,
                token=self._settings.hf_token,
                torch_dtype=dtype,
                device_map=self._settings.hf_device_map,
            )
        return self._hf_tokenizer, self._hf_model

    def _get_hf_vision_components(self):
        if not self._settings.hf_token:
            raise RuntimeError("HF_TOKEN is required for Hugging Face MedGemma generation.")
        if self._hf_model is None or self._hf_processor is None:
            import torch
            from transformers import AutoModelForImageTextToText, AutoProcessor

            dtype = _resolve_torch_dtype(torch, self._settings.hf_torch_dtype)
            self._hf_processor = AutoProcessor.from_pretrained(
                self._settings.hf_model_name,
                token=self._settings.hf_token,
            )
            self._hf_model = AutoModelForImageTextToText.from_pretrained(
                self._settings.hf_model_name,
                token=self._settings.hf_token,
                torch_dtype=dtype,
                device_map=self._settings.hf_device_map,
            )
        return self._hf_processor, self._hf_model

    def generate(
        self,
        prompt: str,
        *,
        temperature: float = 0.1,
        max_output_tokens: int = 1024,
        retries: int = 2,
        response_mime_type: str | None = None,
    ) -> LLMResponse:

        if self.provider in {"hf", "huggingface", "medgemma"}:
            return self._generate_huggingface(
                prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                retries=retries,
            )

        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                from google.genai import types

                client = self._get_client()
                response = client.models.generate_content(
                    model=self._settings.gemini_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                        response_mime_type=response_mime_type,
                        safety_settings=[
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            )
                        ]
                    )
                    ,
                )
                text = getattr(response, "text", "") or ""
                return LLMResponse(text=text.strip(), raw=response)
            except Exception as exc:
                last_exc = exc
                if attempt < retries:
                    time.sleep(2**attempt)
        raise RuntimeError(f"Gemini failed after {retries + 1} attempts: {last_exc}")

    def generate_multimodal(
        self,
        prompt: str,
        *,
        image_bytes_list: list[bytes] | None = None,
        temperature: float = 0.1,
        max_output_tokens: int = 1024,
        retries: int = 2,
    ) -> LLMResponse:

        if self.provider in {"hf", "huggingface", "medgemma"}:
            if image_bytes_list:
                return self._generate_huggingface_multimodal(
                    prompt,
                    image_bytes_list=image_bytes_list,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    retries=retries,
                )
            return self._generate_huggingface(
                prompt,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                retries=retries,
            )

        from google.genai import types

        parts = [types.Part.from_text(text=prompt)]
        for image_bytes in image_bytes_list or []:
            parts.append(
                types.Part.from_bytes(data=image_bytes, mime_type=_detect_mime(image_bytes))
            )

        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                client = self._get_client()
                response = client.models.generate_content(
                    model=self._settings.gemini_model,
                    contents=parts,
                    config=types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                        safety_settings=[
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            ),
                            types.SafetySetting(
                                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                                threshold=types.HarmBlockThreshold.BLOCK_NONE,
                            )
                        ]
                    )
                    ,
                )
                text = getattr(response, "text", "") or ""
                return LLMResponse(text=text.strip(), raw=response)
            except Exception as exc:
                last_exc = exc
                if attempt < retries:
                    time.sleep(2**attempt)
        raise RuntimeError(
            f"Gemini multimodal failed after {retries + 1} attempts: {last_exc}"
        )

    def generate_json(
        self,
        prompt: str,
        *,
        temperature: float = 0.0,
        max_output_tokens: int = 800,
    ) -> dict[str, Any]:
        response = self.generate(
            prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
        )
        return _parse_json_object(response.text)

    def _generate_huggingface(
        self,
        prompt: str,
        *,
        temperature: float,
        max_output_tokens: int,
        retries: int,
    ) -> LLMResponse:
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                tokenizer, model = self._get_hf_components()
                input_ids = _tokenize_prompt(tokenizer, prompt, model)
                input_length = int(input_ids.shape[-1])
                do_sample = temperature > 0
                generate_kwargs = {
                    "max_new_tokens": max_output_tokens,
                    "do_sample": do_sample,
                    "pad_token_id": tokenizer.eos_token_id,
                }
                if do_sample:
                    generate_kwargs["temperature"] = temperature
                outputs = model.generate(input_ids, **generate_kwargs)
                generated = outputs[0][input_length:]
                text = tokenizer.decode(generated, skip_special_tokens=True).strip()
                return LLMResponse(text=text, raw=outputs)
            except Exception as exc:
                last_exc = exc
                if attempt < retries:
                    time.sleep(2**attempt)
        raise RuntimeError(
            f"Hugging Face model '{self._settings.hf_model_name}' failed after "
            f"{retries + 1} attempts: {last_exc}"
        )

    def _generate_huggingface_multimodal(
        self,
        prompt: str,
        *,
        image_bytes_list: list[bytes],
        temperature: float,
        max_output_tokens: int,
        retries: int,
    ) -> LLMResponse:
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                import torch
                from PIL import Image

                processor, model = self._get_hf_vision_components()
                images = [
                    Image.open(BytesIO(image_bytes)).convert("RGB")
                    for image_bytes in image_bytes_list
                ]
                content = [{"type": "image", "image": image} for image in images]
                content.append({"type": "text", "text": prompt})
                messages = [{"role": "user", "content": content}]
                inputs = processor.apply_chat_template(
                    messages,
                    add_generation_prompt=True,
                    tokenize=True,
                    return_dict=True,
                    return_tensors="pt",
                )
                device = getattr(model, "device", None)
                if device is not None:
                    inputs = {
                        key: value.to(device) if hasattr(value, "to") else value
                        for key, value in inputs.items()
                    }
                input_length = int(inputs["input_ids"].shape[-1])
                generate_kwargs = {
                    "max_new_tokens": max_output_tokens,
                    "do_sample": temperature > 0,
                    "pad_token_id": getattr(processor.tokenizer, "eos_token_id", None),
                }
                if temperature > 0:
                    generate_kwargs["temperature"] = temperature
                with torch.no_grad():
                    outputs = model.generate(**inputs, **generate_kwargs)
                generated = outputs[0][input_length:]
                text = processor.decode(generated, skip_special_tokens=True).strip()
                return LLMResponse(text=text, raw=outputs)
            except Exception as exc:
                last_exc = exc
                if attempt < retries:
                    time.sleep(2**attempt)
        raise RuntimeError(
            f"Hugging Face multimodal model '{self._settings.hf_model_name}' failed after "
            f"{retries + 1} attempts: {last_exc}"
        )


def _parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object from Gemini output, tolerating fenced JSON blocks."""

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`").strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("LLM JSON response must be an object.")
    return parsed


def _resolve_torch_dtype(torch_module: Any, dtype_name: str) -> Any:
    normalized = dtype_name.strip().lower()
    if normalized in {"", "auto"}:
        if torch_module.cuda.is_available():
            return torch_module.bfloat16
        return torch_module.float32
    return getattr(torch_module, normalized)


def _tokenize_prompt(tokenizer: Any, prompt: str, model: Any) -> Any:
    messages = [{"role": "user", "content": prompt}]
    try:
        encoded = tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            return_tensors="pt",
        )
    except Exception:
        encoded = tokenizer(prompt, return_tensors="pt").input_ids

    device = getattr(model, "device", None)
    if device is not None:
        encoded = encoded.to(device)
    return encoded




def _detect_mime(data: bytes) -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"
