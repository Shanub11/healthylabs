import asyncio
import os
from neo4j import AsyncGraphDatabase


async def run_diagnostics():
    # Update these if your local Neo4j uses different credentials
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")  # Put your actual password here

    print(f"Connecting to Neo4j at {uri}...")

    try:
        driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

        async with driver.session() as session:
            print("✅ 1. Connection: SUCCESS")

            # Check for existing Vector Indexes
            index_query = "SHOW INDEXES YIELD name, type WHERE type = 'VECTOR' RETURN name"
            index_result = await session.run(index_query)
            indexes = [record["name"] async for record in index_result]

            if indexes:
                print(f"✅ 2. Vector Indexes: {indexes}")
            else:
                print("❌ 2. Vector Indexes: NONE FOUND")
                print("   WARNING: Your vector service will fail without an index!")

            # Check database population
            count_query = "MATCH (n) RETURN labels(n) AS label, count(*) AS count"
            count_result = await session.run(count_query)

            print("📊 3. Database Snapshot:")
            empty = True
            async for record in count_result:
                empty = False
                print(f"   - {record['label'][0] if record['label'] else 'Unknown'}: {record['count']} nodes")

            if empty:
                print("   - Graph is completely empty.")

    except Exception as e:
        print(f"❌ CONNECTION FAILED: {e}")

    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(run_diagnostics())