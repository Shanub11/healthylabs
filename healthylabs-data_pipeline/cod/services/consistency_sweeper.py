import logging
import os

from neo4j import GraphDatabase

from cod.core.database import MedicalMetadata, SessionLocal
from cod.core.models import DocStatus

logger = logging.getLogger("ConsistencySweeper")


def _get_driver():
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    if not uri or not user or not password:
        raise RuntimeError("NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD must be set before calling sweep_missing_vectors()")
    return GraphDatabase.driver(uri, auth=(user, password))


def sweep_missing_vectors():
    db = SessionLocal()
    driver = _get_driver()
    try:
        active_docs = db.query(MedicalMetadata).filter(MedicalMetadata.status == DocStatus.ACTIVE).all()
        with driver.session() as session:
            for doc in active_docs:
                result = session.run(
                    """
                    MATCH (d:Document {document_id: $document_id})
                    RETURN count(d) AS cnt
                    """,
                    document_id=doc.document_id,
                )
                if result.single()["cnt"] == 0:
                    logger.warning("[CONSISTENCY] Missing vectors for %s (%s)", doc.doc_uid, doc.document_id)
    finally:
        db.close()
        driver.close()
