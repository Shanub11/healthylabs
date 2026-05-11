class PipelineError(Exception):
    """Base class for all pipeline errors"""


# ---------- Ingestion ----------
class IngestionError(PipelineError):
    pass


class DuplicateDocumentError(IngestionError):
    pass


class InvalidDocumentError(IngestionError):
    pass


# ---------- Safety ----------
class SafetyViolationError(PipelineError):
    pass


# ---------- Vectorization ----------
class VectorError(PipelineError):
    pass


class VectorTransientError(VectorError):
    """Retryable errors (network, timeouts)"""


class VectorPermanentError(VectorError):
    """Non-retryable errors (schema, data corruption)"""
