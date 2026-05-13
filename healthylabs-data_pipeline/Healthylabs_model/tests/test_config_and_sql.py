import pytest

from healthylabs_inference.core.database_clients import _safe_table_identifier


def test_safe_table_identifier_quotes_pipeline_metadata_table():
    assert _safe_table_identifier("medical_metadata") == '"medical_metadata"'


def test_safe_table_identifier_rejects_injection():
    with pytest.raises(ValueError):
        _safe_table_identifier('MedicalMetadata; DROP TABLE "MedicalMetadata"')
