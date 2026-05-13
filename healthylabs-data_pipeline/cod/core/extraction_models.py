from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    """Base model that forbids undeclared fields everywhere."""

    model_config = ConfigDict(extra="forbid")


class ValueWithConfidence(StrictModel):
    value: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)


class DateWithConfidence(StrictModel):
    value: date | datetime
    confidence: float = Field(..., ge=0.0, le=1.0)


class DocumentMetadata(StrictModel):
    title: ValueWithConfidence
    authors: List[ValueWithConfidence] = Field(default_factory=list)
    published_at: Optional[DateWithConfidence] = None
    tags: List[str] = Field(default_factory=list)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: List[str]) -> List[str]:
        cleaned = [tag.strip() for tag in tags if tag and tag.strip()]
        if len(cleaned) != len(tags):
            raise ValueError("metadata.tags must contain non-empty strings only.")
        return cleaned


class QualityMetrics(StrictModel):
    overall_score: float = Field(..., ge=0.0, le=1.0)
    ocr_mean_confidence: float = Field(..., ge=0.0, le=1.0)
    issues: List[str] = Field(default_factory=list)


class LayoutNode(StrictModel):
    node_id: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    bbox: List[float] = Field(..., min_length=4, max_length=4)
    page: int = Field(..., ge=1)
    reading_order: int = Field(..., ge=0)
    section_id: Optional[str] = None
    referenced_assets: List[str] = Field(default_factory=list)


class LayoutEdge(StrictModel):
    from_node: str = Field(..., alias="from", min_length=1)
    to_node: str = Field(..., alias="to", min_length=1)
    relation: str = Field(..., min_length=1)


class LayoutGraph(StrictModel):
    nodes: List[LayoutNode] = Field(default_factory=list)
    edges: List[LayoutEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_edge_nodes(self) -> "LayoutGraph":
        node_ids = {node.node_id for node in self.nodes}
        for edge in self.edges:
            if edge.from_node not in node_ids:
                raise ValueError(
                    f"layout_graph.edges contains unknown source node '{edge.from_node}'. "
                    "Add the node to layout_graph.nodes or fix the edge reference."
                )
            if edge.to_node not in node_ids:
                raise ValueError(
                    f"layout_graph.edges contains unknown destination node '{edge.to_node}'. "
                    "Add the node to layout_graph.nodes or fix the edge reference."
                )
        return self


class SectionHierarchyNode(StrictModel):
    id: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    heading: Optional[str] = None
    children: List["SectionHierarchyNode"] = Field(default_factory=list)


class DosageIndicator(StrictModel):
    text: str = Field(..., min_length=1)
    layout_node: str = Field(..., min_length=1)
    units: str = Field(..., min_length=1)
    unit_normalized: str = Field(..., min_length=1)
    numeric_value: str = Field(..., min_length=1)


class MedicalPatterns(StrictModel):
    dosage_indicators: List[DosageIndicator] = Field(default_factory=list)
    units_detected: List[str] = Field(default_factory=list)


class AuditSource(StrictModel):
    provider: str = Field(..., min_length=1)
    uri: str = Field(..., min_length=1)


class ExtractionRuntime(StrictModel):
    engine: str = Field(..., min_length=1)
    engine_version: str = Field(..., min_length=1)
    extracted_at: datetime


class AuditTrail(StrictModel):
    document_id: str = Field(..., min_length=1)
    source: AuditSource
    extraction: ExtractionRuntime


class AssetDerivative(StrictModel):
    format: str = Field(..., min_length=1)
    path: str = Field(..., min_length=1)
    hash: str = Field(..., min_length=1)


class Asset(StrictModel):
    asset_id: str = Field(..., min_length=1)
    kind: str = Field(..., min_length=1)
    page: int = Field(..., ge=1)
    path: str = Field(..., min_length=1)
    hash: str = Field(..., min_length=1)
    derivatives: List[AssetDerivative] = Field(default_factory=list)
    caption: Optional[str] = None


class TableCell(StrictModel):
    row: int = Field(..., ge=0)
    column: int = Field(..., ge=0)
    text: str = Field(..., min_length=1)


class TableModel(StrictModel):
    table_id: str = Field(..., min_length=1)
    layout_node: Optional[str] = None
    section_id: Optional[str] = None
    markdown: str = Field(..., min_length=1)
    page: int = Field(..., ge=1)
    cells: List[TableCell] = Field(default_factory=list)


class ExtractionOutput(StrictModel):
    document_id: str = Field(..., min_length=3)
    source: str = Field(..., min_length=3)
    content: str = Field(..., min_length=50)
    metadata: DocumentMetadata
    quality: QualityMetrics
    layout_graph: LayoutGraph
    section_hierarchy: Optional[SectionHierarchyNode] = None
    medical_patterns: MedicalPatterns
    audit: AuditTrail
    assets: List[Asset] = Field(default_factory=list)
    tables: List[TableModel] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_cross_references(self) -> "ExtractionOutput":
        if self.audit.document_id != self.document_id:
            raise ValueError(
                "audit.document_id must match document_id for traceability. "
                "Fix extractor identity mapping and retry ingestion."
            )

        if not self.metadata.title.value.strip():
            raise ValueError(
                "metadata.title.value is required and cannot be blank. "
                "Ensure extractor emits a resolved title."
            )

        layout_node_ids = {node.node_id for node in self.layout_graph.nodes}
        for item in self.medical_patterns.dosage_indicators:
            if item.layout_node not in layout_node_ids:
                raise ValueError(
                    f"medical_patterns.dosage_indicators.layout_node '{item.layout_node}' "
                    "is missing from layout_graph.nodes. Include the referenced node."
                )

        for table in self.tables:
            if table.layout_node and table.layout_node not in layout_node_ids:
                raise ValueError(
                    f"tables.layout_node '{table.layout_node}' is missing from layout_graph.nodes. "
                    "Include the node or remove the broken reference."
                )

        return self

SectionHierarchyNode.model_rebuild()
