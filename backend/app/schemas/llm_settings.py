from pydantic import BaseModel


class LLMSettingsOut(BaseModel):
    provider: str
    ollama_model: str
    ollama_base_url: str
    ollama_cloud_model: str
    ollama_cloud_base_url: str
    ollama_cloud_api_key_configured: bool
    reachable: bool


class LLMSettingsUpdate(BaseModel):
    provider: str | None = None
    ollama_model: str | None = None
    ollama_base_url: str | None = None
    ollama_cloud_model: str | None = None
    ollama_cloud_base_url: str | None = None
    ollama_cloud_api_key: str | None = None


class AIStatusOut(BaseModel):
    provider: str
    model: str
    embedding_model: str
    reachable: bool
