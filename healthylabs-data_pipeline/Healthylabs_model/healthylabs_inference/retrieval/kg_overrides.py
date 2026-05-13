"""Patient-specific knowledge-graph safety checks."""

from __future__ import annotations

from dataclasses import dataclass

from healthylabs_inference.api.request_models import QueryRequest
from healthylabs_inference.core.database_clients import Neo4jSearchClient


@dataclass(slots=True)
class KnowledgeGraphOverrides:
    search_client: Neo4jSearchClient

    def collect(self, request: QueryRequest) -> list[dict[str, object]]:
        if not request.patient_id or not request.patient_context:
            return []
        context = request.patient_context
        medications = []
        if hasattr(context, "medications"):
            medications = list(context.medications)
        elif isinstance(context, dict):
            medications = [str(item) for item in context.get("medications", [])]
        return self.search_client.patient_drug_facts(patient_id=request.patient_id, drug_names=medications)
