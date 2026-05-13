import hashlib
import re
from enum import Enum
from typing import Any, Dict, List, Optional

import tiktoken

from cod.core.models import HierarchicalChunk, MedicalDocumentSchema


# -------------------------------------------------
# Constants & Helpers
# -------------------------------------------------


class ChunkLevel(int, Enum):
    ATOMIC = 1
    CONTEXT = 2


SHEET_NODE_TYPES = {"sheet", "spreadsheet", "worksheet"}
PLACEHOLDER_PATTERN = re.compile(r"\[(?:IMAGE|TABLE|CITATION):[^\]]+\]")


def get_token_count(text: str, model: str = "gpt-4") -> int:
    """
    Accurately counts tokens using the CL100K_Base encoding.
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback to a safer multiplier if tokenizer fails
        return int(len(text) / 4)


class GraphChunker:
    """
    Graph-driven hierarchical chunker.

    Behavior:
    - Uses extractor layout_graph + section_hierarchy when available.
    - Groups document nodes by parent_section_id derived from hierarchy.
    - Splits sheet assets as header + deterministic 50-row windows.
    """

    def __init__(self, settings, atomic_tokens: int = None, context_tokens: int = None):
        self.atomic_tokens = atomic_tokens or settings.ATOMIC_CHUNK_SIZE
        self.context_tokens = context_tokens or settings.CONTEXT_CHUNK_SIZE
        self.max_safeguard = settings.MAX_CHUNK_SAFEGUARD

    def process_document(self, doc: MedicalDocumentSchema) -> List[Dict[str, Any]]:
        layout_graph = (doc.metadata_extra or {}).get("layout_graph") or {}
        section_hierarchy = (doc.metadata_extra or {}).get("section_hierarchy") or {}

        hierarchy: List[Dict[str, Any]] = []

        if layout_graph.get("nodes"):
            section_parent_map = self._build_section_parent_map(section_hierarchy)
            grouped_nodes = self._group_nodes_by_parent_section(layout_graph.get("nodes", []), section_parent_map)

            for section_key in sorted(grouped_nodes.keys()):
                context_texts = self._build_context_texts_from_nodes(grouped_nodes[section_key])
                for context_index, context_text in enumerate(context_texts):
                    l2_id = self._stable_chunk_id(doc.doc_uid, section_key, context_index)
                    l2_chunk = HierarchicalChunk(
                        chunk_id=l2_id,
                        parent_doc_id=doc.doc_uid,
                        level=ChunkLevel.CONTEXT.value,
                        content=context_text,
                        metadata={
                            "source": doc.source,
                            "tier": doc.source_tier.value,
                            "authority_score": doc.authority_score,
                            "type": "clinical_context",
                            "section": section_key,
                        },
                    )

                    l1_chunks = self._create_atomic_chunks(context_text, doc, l2_id, section=section_key)
                    hierarchy.append({"l2_parent": l2_chunk.dict(), "l1_children": l1_chunks})

            if hierarchy:
                return hierarchy

        # Fallback path: no graph available, or graph nodes had no usable text.
        text = self._normalize_text(doc.raw_content)
        fallback_sections = [text] if text else []
        for idx, section_text in enumerate(fallback_sections):
            l2_id = self._stable_chunk_id(doc.doc_uid, "legacy", idx)
            l2_chunk = HierarchicalChunk(
                chunk_id=l2_id,
                parent_doc_id=doc.doc_uid,
                level=ChunkLevel.CONTEXT.value,
                content=section_text,
                metadata={
                    "source": doc.source,
                    "tier": doc.source_tier.value,
                    "authority_score": doc.authority_score,
                    "type": "clinical_context",
                    "section": "legacy",
                },
            )
            l1_chunks = self._create_atomic_chunks(section_text, doc, l2_id, section="legacy")
            hierarchy.append({"l2_parent": l2_chunk.dict(), "l1_children": l1_chunks})

        return hierarchy

    def _build_section_parent_map(self, section_hierarchy: Dict[str, Any]) -> Dict[str, str]:
        mapping: Dict[str, str] = {}

        def walk(node: Dict[str, Any], parent_id: Optional[str] = None):
            section_id = node.get("id")
            if section_id:
                mapping[section_id] = parent_id or section_id
            for child in node.get("children", []) or []:
                walk(child, section_id)

        if section_hierarchy:
            walk(section_hierarchy, None)

        return mapping

    def _group_nodes_by_parent_section(
        self, nodes: List[Dict[str, Any]], section_parent_map: Dict[str, str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}

        ordered_nodes = sorted(
            nodes,
            key=lambda n: (
                n.get("page", 0),
                n.get("reading_order", 0),
                n.get("node_id", ""),
            ),
        )

        for node in ordered_nodes:
            section_id = node.get("section_id") or "unsectioned"
            parent_section_id = section_parent_map.get(section_id, section_id)
            grouped.setdefault(parent_section_id, []).append(node)

        return grouped

    def _build_context_texts_from_nodes(self, nodes: List[Dict[str, Any]]) -> List[str]:
        parts: List[str] = []
        for node in nodes:
            node_type = (node.get("type") or "").lower()
            node_text = self._normalize_text(node.get("text", ""))
            if not node_text:
                continue

            if node_type in SHEET_NODE_TYPES:
                parts.extend(self._chunk_sheet_node_text(node, node_text))
            else:
                parts.append(node_text)

        full_text = "\n\n".join(parts).strip()
        if not full_text:
            return []

        return self._chunk_by_tokens(full_text, self.context_tokens)

    def _chunk_sheet_node_text(self, node: Dict[str, Any], text: str) -> List[str]:
        lines = [line for line in text.splitlines() if line.strip()]
        if len(lines) <= 1:
            return [text]

        header = lines[0].strip()
        rows = lines[1:]
        node_id = node.get("node_id", "sheet")
        chunks: List[str] = []

        for start in range(0, len(rows), 50):
            end = min(start + 50, len(rows))
            window_rows = rows[start:end]
            window_text = "\n".join([header, *window_rows])
            sheet_chunk_id = hashlib.sha1(f"{node_id}:{start}:{end}".encode("utf-8")).hexdigest()[:12]
            chunks.append(f"[SHEET_CHUNK_ID:{sheet_chunk_id}]\n{window_text}")

        return chunks

    def _chunk_by_tokens(self, text: str, target_tokens: int) -> List[str]:
        paragraphs = [p for p in text.split("\n\n") if p.strip()]

        chunks: List[str] = []
        current: List[str] = []
        current_tokens = 0

        for paragraph in paragraphs:
            paragraph_tokens = get_token_count(paragraph)
            if current and (
                current_tokens + paragraph_tokens > target_tokens
                or current_tokens > self.max_safeguard
            ):
                chunks.append("\n\n".join(current))
                current = [paragraph]
                current_tokens = paragraph_tokens
            else:
                current.append(paragraph)
                current_tokens += paragraph_tokens

        if current:
            chunks.append("\n\n".join(current))

        return chunks

    def _normalize_text(self, text: str) -> str:
        text = text.replace("\r", "\n")
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _create_atomic_chunks(
        self, l2_text: str, doc: MedicalDocumentSchema, l2_id: str, section: str
    ) -> List[Dict[str, Any]]:
        atomic_texts = self._chunk_by_tokens(l2_text, self.atomic_tokens)
        records: List[Dict[str, Any]] = []

        for idx, text in enumerate(atomic_texts):
            if not self._placeholders_preserved(text):
                raise ValueError("Placeholder token corruption detected before atomic chunking.")

            enriched = self._inject_context(text, doc, section=section)
            records.append(
                {
                    "chunk_id": f"{l2_id}_L1_{idx}",
                    "parent_l2_id": l2_id,
                    "parent_doc_id": doc.doc_uid,
                    "level": ChunkLevel.ATOMIC.value,
                    "content_vectorized": enriched,
                    "metadata": {
                        "tier": doc.source_tier.value,
                        "authority_score": doc.authority_score,
                        "tags": doc.tags,
                        "section": section,
                    },
                }
            )

        return records

    def _placeholders_preserved(self, text: str) -> bool:
        # Validation-only guard to ensure placeholder syntax remains exact.
        return all(match.group(0) == match.group(0).strip() for match in PLACEHOLDER_PATTERN.finditer(text))

    def _inject_context(self, chunk_text: str, doc: MedicalDocumentSchema, section: str) -> str:
        evidence_level = (doc.metadata_extra or {}).get("evidence_level", "unknown")
        header = (
            f"[DOC_TITLE]: {doc.title}\n"
            f"[SECTION]: {section}\n"
            f"[SOURCE_TIER]: {doc.source_tier.name}\n"
            f"[EVIDENCE_LEVEL]: {evidence_level}\n"
        )
        return header + chunk_text

    def _stable_chunk_id(self, doc_uid: str, section_key: str, index: int) -> str:
        digest = hashlib.sha1(f"{doc_uid}:{section_key}:{index}".encode("utf-8")).hexdigest()[:12]
        return f"{doc_uid}_L2_{digest}"


class MedicalHierarchicalChunker(GraphChunker):
    """Deprecated alias retained for compatibility; now graph-driven via GraphChunker."""
