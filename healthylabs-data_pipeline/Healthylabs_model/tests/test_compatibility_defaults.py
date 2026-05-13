from healthylabs_inference.core.config import Settings


def test_pipeline_compatible_defaults():
    settings = Settings()

    assert settings.vector_index_name == "atomic_chunk_embeddings"
    assert settings.metadata_table_name == "medical_metadata"
    assert settings.allowed_index_domains == []
    assert settings.visual_asset_index_name == "medical_asset_embeddings"
    assert settings.visual_score_threshold == 0.60
