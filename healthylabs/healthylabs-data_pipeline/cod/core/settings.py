from typing import Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    model_config = SettingsConfigDict(extra='ignore', env_file='.env')
    # --- App ---
    ENV: str = Field(..., pattern="^(dev|staging|prod)$")

    # --- Database ---
    DATABASE_URL: str

    # --- Neo4j ---
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str

    # --- Security ---
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # --- Safety ---
    PHI_CONFIDENCE_THRESHOLD: float = Field(0.05, ge=0.00, le=1.0) #should be 0.95, .8, 1

    @property
    def HARD_CONFIDENCE_THRESHOLD(self) -> float:
        return self.PHI_CONFIDENCE_THRESHOLD

    NCBI_API_KEY: Optional[str] = Field(None, env="NCBI_API_KEY")

    # --- Safety Weights ---
    PHI_WEIGHTS: dict = Field(default_factory=lambda: {
        "NAME": 0.15,
        "DOB": 0.20,
        "SSN": 0.40,
        "PHONE": 0.10,
        "PATIENT_ID": 0.30,
        "ADDRESS": 0.15,
        "EMAIL": 0.10
    })

    # --- Chunker Defaults ---
    ATOMIC_CHUNK_SIZE: int = 256
    CONTEXT_CHUNK_SIZE: int = 768
    MAX_CHUNK_SAFEGUARD: int = 1024

    @validator("DATABASE_URL", "NEO4J_URI", "JWT_SECRET_KEY")
    def must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Critical config value missing")
        return v

