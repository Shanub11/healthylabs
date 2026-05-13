from healthylabs_inference.core.config import Settings
from healthylabs_inference.core.database_clients import MinioImageClient
from healthylabs_inference.retrieval.strategies.visual import VisualRetrievalStrategy


class FakeEmbedder:
    def embed_text(self, text):
        return [0.1] * 512


class FakeRecord(dict):
    pass


class FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, cypher, **params):
        self.params = params
        return [
            FakeRecord(
                storage_path="s3://bucket/path/image.png",
                caption="Chest x-ray image",
                doc_uid="doc-1",
                score=0.91,
            ),
            FakeRecord(
                storage_path="s3://bucket/path/missing.png",
                caption="Missing image",
                doc_uid="doc-2",
                score=0.8,
            ),
        ]


class FakeDriver:
    def __init__(self):
        self.session_obj = FakeSession()

    def session(self, database=None):
        return self.session_obj


class FakeNeo4jClient:
    def __init__(self):
        self.driver = FakeDriver()

    def _get_driver(self):
        return self.driver


class FakeMinioClient:
    def get_image_bytes(self, storage_path):
        if "missing" in storage_path:
            raise RuntimeError("not found")
        return b"\x89PNG\r\n\x1a\nimage"

    def generate_presigned_url(self, storage_path):
        return f"https://signed/{storage_path}"


def test_minio_image_client_parses_s3_storage_path():
    client = MinioImageClient(Settings())

    assert client._parse_path("s3://healthylabs-images/a/b.png") == (
        "healthylabs-images",
        "a/b.png",
    )


def test_visual_retrieval_queries_neo4j_and_fetches_minio_bytes():
    strategy = VisualRetrievalStrategy(
        clip_embedder=FakeEmbedder(),
        neo4j_client=FakeNeo4jClient(),
        minio_client=FakeMinioClient(),
        settings=Settings(visual_score_threshold=0.75),
    )

    results = strategy.run("show chest xray")

    assert len(results) == 1
    assert results[0].caption == "Chest x-ray image"
    assert results[0].image_bytes.startswith(b"\x89PNG")
    assert results[0].presigned_url == "https://signed/s3://bucket/path/image.png"
