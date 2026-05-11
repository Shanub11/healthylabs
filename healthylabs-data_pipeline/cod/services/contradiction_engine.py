import logging
import os
from typing import List, Dict

from neo4j import AsyncGraphDatabase

logger = logging.getLogger("ContradictionEngine")


class ContradictionCluster:
    def __init__(self, drug: str, conflicts: List[Dict]):
        self.drug = drug
        self.conflicts = conflicts
        self.severity = self._compute_severity()

    def _compute_severity(self) -> str:
        if not self.conflicts:
            return "none"
        max_diff = max(c.get("diff_fraction", 0.0) for c in self.conflicts)
        if max_diff > 0.5:
            return "high"
        if max_diff > 0.2:
            return "medium"
        return "low"

    def to_dict(self) -> Dict:
        return {"drug": self.drug, "severity": self.severity, "conflict_count": len(self.conflicts), "conflicts": self.conflicts}


class ContradictionEngine:
    DOSE_DIFF_THRESHOLD = float(os.getenv("CONTRADICTION_THRESHOLD", "0.20"))

    UNIT_FACTORS = {"mg": 1.0, "mcg": 0.001, "ug": 0.001, "g": 1000.0}

    def __init__(self, uri: str, user: str, password: str):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def close(self):
        await self.driver.close()

    def _normalize(self, dose, unit):
        try:
            d = float(dose)
        except Exception:
            return None
        u = (unit or "").lower().strip()
        if u in self.UNIT_FACTORS:
            return d * self.UNIT_FACTORS[u]
        if u == "":
            return d
        return None

    async def check_document(self, document_id: str) -> List[ContradictionCluster]:
        new_doses = await self._get_document_doses(document_id)
        if not new_doses:
            return []
        clusters = []
        for drug_name, dose_info in new_doses.items():
            existing = await self._get_existing_doses(drug_name, document_id, min_authority=0.7)
            conflicts = []
            new_norm = self._normalize(dose_info.get("dosage"), dose_info.get("unit"))
            if new_norm is None or new_norm == 0:
                continue
            for e in existing:
                ex_norm = self._normalize(e.get("dosage"), e.get("unit"))
                if ex_norm is None or ex_norm == 0:
                    continue
                diff = abs(new_norm - ex_norm) / max(new_norm, ex_norm)
                if diff > self.DOSE_DIFF_THRESHOLD:
                    conflicts.append({"dose_a": dose_info.get("dosage"), "dose_b": e.get("dosage"), "unit_a": dose_info.get("unit", ""), "unit_b": e.get("unit", ""), "document_id_b": e.get("document_id"), "diff_fraction": round(diff, 3)})
            if conflicts:
                clusters.append(ContradictionCluster(drug_name, conflicts))
        return clusters

    async def _get_document_doses(self, document_id: str) -> Dict[str, Dict]:
        query = """
        MATCH (d:Drug)-[r:PRESCRIBED]->(:Patient)
        WHERE r.document_id = $document_id
        RETURN d.name AS drug, r.dosage AS dosage, r.unit AS unit
        """
        async with self.driver.session() as session:
            result = await session.run(query, document_id=document_id)
            records = await result.data()
        return {r["drug"]: {"dosage": r.get("dosage"), "unit": r.get("unit")} for r in records if r.get("drug")}

    async def _get_existing_doses(self, drug_name: str, exclude_doc_id: str, min_authority: float) -> List[Dict]:
        query = """
        MATCH (d:Drug {name: $drug_name})-[r:PRESCRIBED]->(:Patient)
        WHERE r.document_id <> $exclude_doc_id
          AND r.authority_score >= $min_authority
        RETURN r.dosage AS dosage, r.unit AS unit, r.document_id AS document_id
        LIMIT 50
        """
        async with self.driver.session() as session:
            result = await session.run(query, drug_name=drug_name, exclude_doc_id=exclude_doc_id, min_authority=min_authority)
            return await result.data()
