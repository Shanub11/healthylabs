from sqlalchemy.orm import Session

from cod.core.database import MedicalMetadata, MedicalMetadataAudit
from cod.core.models import DocStatus


def update_status(
    db: Session,
    document_id: str,
    new_status: DocStatus,
    reason: str,
    actor: str = "system",
):
    metadata = db.query(MedicalMetadata).filter(
        MedicalMetadata.document_id == document_id
    ).first()

    if not metadata:
        return

    old_status = metadata.status

    if old_status == new_status:
        return  # no-op

    metadata.status = new_status

    audit = MedicalMetadataAudit(
        document_id=metadata.document_id,
        doc_uid=metadata.doc_uid,
        previous_status=old_status.value if old_status else None,
        new_status=new_status.value,
        reason=reason,
        actor=actor,
    )

    db.add(audit)
