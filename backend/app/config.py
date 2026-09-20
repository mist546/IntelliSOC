from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / ".env"), extra="ignore")

    APP_NAME: str = "IntelliSOC"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    DATABASE_URL: str = f"sqlite:///{(BASE_DIR / 'data' / 'mini_soc.db').as_posix()}"

    SECRET_KEY: str = "dev-secret-key-change-in-production-please"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_UPLOAD_EXTENSIONS: list[str] = [".log", ".txt", ".csv", ".json"]

    # Ollama (local)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma4:latest"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    OLLAMA_TIMEOUT: int = 240
    OLLAMA_TEMPERATURE: float = 0.1
    OLLAMA_MAX_TOKENS: int = 1300

    # Ollama cloud (optional alternative provider, OpenAI-compatible or ollama.com cloud)
    LLM_PROVIDER: str = "ollama_local"  # ollama_local | ollama_cloud
    OLLAMA_CLOUD_BASE_URL: str = "https://ollama.com"
    OLLAMA_CLOUD_API_KEY: str = ""
    OLLAMA_CLOUD_MODEL: str = "qwen3:4b"

    # RAG
    CHROMA_PERSIST_DIR: str = str((BASE_DIR / "rag" / "chroma_db"))
    RAG_COLLECTION_NAME: str = "security_knowledge"
    RAG_TOP_K: int = 4
    KNOWLEDGE_BASE_DIR: str = str((BASE_DIR / "data" / "knowledge_base"))

    # Threat Intel
    VIRUSTOTAL_API_KEY: str = ""
    NVD_API_KEY: str = ""
    THREAT_INTEL_DIR: str = str((BASE_DIR / "data" / "threat_intel"))

    # Detection thresholds
    SSH_BRUTE_FORCE_THRESHOLD: int = 10
    SSH_BRUTE_FORCE_WINDOW_MINUTES: int = 5

    # Website scanner
    SCAN_ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]
    SCAN_TIMEOUT_SECONDS: int = 10

    REPORTS_DIR: str = str((BASE_DIR / "data" / "reports"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
