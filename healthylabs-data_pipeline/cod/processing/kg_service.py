import logging
import re
from typing import Any, Dict, List

from neo4j import AsyncGraphDatabase

from cod.core.extraction_models import DocumentMetadata, MedicalPatterns

logger = logging.getLogger("MedicalKGService")
logger.setLevel(logging.INFO)


class MedicalKGService:
    """
    Writes extractor-produced graph facts to Neo4j without reparsing raw content.
    """

    def __init__(self, uri: str, user: str, password: str):
        self.driver = AsyncGraphDatabase.driver(
            uri,
            auth=(user, password),
            max_connection_pool_size=20,
            connection_timeout=15,
        )

    async def close(self) -> None:
        await self.driver.close()

    @staticmethod
    def _derive_patient_id(document_id: str, metadata: DocumentMetadata) -> str:
        # Uses extractor metadata/tags only (no raw text parsing).
        for tag in metadata.tags:
            normalized = tag.strip()
            if normalized.lower().startswith("patient:"):
                value = normalized.split(":", 1)[1].strip()
                if value:
                    return value
        return document_id

    @staticmethod
    def _derive_drug_name(indicator_text: str) -> str:
        # Extract from medical_patterns indicator text only.
        cleaned = indicator_text.strip()
        candidate = re.sub(r"\d.*$", "", cleaned).strip(" -,:;")
        return candidate or cleaned or "unknown"

    @staticmethod
    def _build_prescription_payload(
        medical_patterns: MedicalPatterns,
    ) -> List[Dict[str, Any]]:
        payload: List[Dict[str, Any]] = []
        for indicator in medical_patterns.dosage_indicators:
            payload.append(
                {
                    "drug_name": MedicalKGService._derive_drug_name(indicator.text),
                    "dosage": indicator.numeric_value,
                    "frequency": "unknown",
                    "unit": indicator.unit_normalized,
                }
            )
        return payload

    async def upsert_medication_graph(
        self,
        *,
        document_id: str,
        metadata: DocumentMetadata,
        medical_patterns: MedicalPatterns,
        authority_score: float,
    ) -> Dict[str, Any]:
        patient_id = self._derive_patient_id(document_id=document_id, metadata=metadata)
        prescriptions = self._build_prescription_payload(medical_patterns)

        if not prescriptions:
            return {
                "status": "skipped",
                "reason": "no_dosage_indicators",
                "patient_id": patient_id,
                "relationships_written": 0,
            }

        query = """
        MERGE (p:Patient {id: $patient_id})
        WITH p
        UNWIND $prescriptions AS prescription
        MERGE (d:Drug {name: prescription.drug_name})
        MERGE (d)-[r:PRESCRIBED]->(p)
        SET r.dosage = prescription.dosage,
            r.frequency = prescription.frequency,
            r.unit = prescription.unit,
            r.document_id = $document_id,
            r.authority_score = $authority_score,
            r.updated_at = datetime()
        RETURN count(r) AS relationship_count
        """

        async with self.driver.session() as session:
            async def _write(tx):
                result = await tx.run(
                    query,
                    patient_id=patient_id,
                    document_id=document_id,
                    prescriptions=prescriptions,
                    authority_score=authority_score,
                )
                record = await result.single()
                return record["relationship_count"] if record else 0

            relationship_count = await session.execute_write(_write)

        logger.info(
            "KG upsert completed | document_id=%s patient_id=%s relationships=%s",
            document_id,
            patient_id,
            relationship_count,
        )

        return {
            "status": "success",
            "patient_id": patient_id,
            "relationships_written": int(relationship_count),
            "prescriptions_received": len(prescriptions),
        }
