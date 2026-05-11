import asyncio
from neo4j import AsyncGraphDatabase


async def check_neo4j():
    # Replace with your actual Neo4j credentials from your .env
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "HealthyLabsSecure123"  # Put your Neo4j password here

    doc_id = "e1eab31d5f8d1b5e2e686bef9f1282c51403f25e78d25d275e9130093e5bf727"

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async with driver.session() as session:
        # Check if the parent Document node exists
        doc_result = await session.run(
            "MATCH (d:Document {document_id: $doc_id}) RETURN d.doc_uid AS uid",
            doc_id=doc_id
        )
        doc_record = await doc_result.single()
        print(f"Document Node in Graph: {'YES' if doc_record else 'NO'}")

        # Check if any vectorized chunks exist
        chunk_result = await session.run(
            "MATCH (a:AtomicChunk {document_id: $doc_id}) RETURN count(a) AS chunk_count",
            doc_id=doc_id
        )
        chunk_record = await chunk_result.single()
        print(f"Vectorized Chunks Created: {chunk_record['chunk_count']}")

    await driver.close()


if __name__ == "__main__":
    asyncio.run(check_neo4j())