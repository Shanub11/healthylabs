"""BioLORD embedding adapter."""

from __future__ import annotations

from dataclasses import dataclass, field

from healthylabs_inference.core.config import Settings


@dataclass(slots=True)
class BioLORDEmbedder:
    """Lazily loads the BioLORD sentence-transformers model.

    The upstream graph index expects 768-dimensional vectors. The adapter
    validates dimensions at runtime to catch accidental model mismatches before
    a Neo4j vector query is issued.
    """

    settings: Settings
    expected_dimensions: int = 768
    _model: object | None = field(init=False, default=None)

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.settings.biolord_model_name)
        return self._model

    def embed_query(self, text: str) -> list[float]:
        model = self._get_model()
        vector = model.encode(text, normalize_embeddings=True)
        values = [float(item) for item in vector.tolist()]
        if len(values) != self.expected_dimensions:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.expected_dimensions}, got {len(values)}."
            )
        return values


from dataclasses import dataclass, field


@dataclass(slots=True)
class CLIPTextEmbedder:
    """Encodes text queries into CLIP embedding space for visual search."""

    model_name: str = "openai/clip-vit-base-patch32"
    _tokenizer: object | None = field(init=False, default=None)
    _model: object | None = field(init=False, default=None)

    def _get_components(self):
        if self._model is None:
            # We bypass sentence-transformers and load ONLY the text components
            from transformers import CLIPTextModelWithProjection, CLIPTokenizer
            self._tokenizer = CLIPTokenizer.from_pretrained(self.model_name)
            self._model = CLIPTextModelWithProjection.from_pretrained(self.model_name)
        return self._tokenizer, self._model

    def embed_text(self, text: str) -> list[float]:
        tokenizer, model = self._get_components()

        # Tokenize and run through the text model
        inputs = tokenizer([text], padding=True, return_tensors="pt")
        outputs = model(**inputs)

        # Normalize the embeddings to match Neo4j's cosine similarity expectations
        embeds = outputs.text_embeds
        embeds = embeds / embeds.norm(p=2, dim=-1, keepdim=True)

        return [float(v) for v in embeds[0].detach().numpy()]