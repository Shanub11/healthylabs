from cod.core.database import SessionLocal, MedicalMetadata

def reset_document():
    doc_id = "e1eab31d5f8d1b5e2e686bef9f1282c51403f25e78d25d275e9130093e5bf727"
    with SessionLocal() as db:
        # Find the stuck document
        doc = db.query(MedicalMetadata).filter_by(document_id=doc_id).first()
        if doc:
            db.delete(doc)
            db.commit()
            print(f"Successfully deleted {doc_id} from PostgreSQL.")
            print("You are clear to run the pipeline again!")
        else:
            print("Document not found in Postgres.")

if __name__ == "__main__":
    reset_document()