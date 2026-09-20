import httpx

from app.config import get_settings
from app.services.llm.base import LLMProvider, LLMUnavailableError
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class OllamaCloudProvider(LLMProvider):
    """Alternative to the local Ollama daemon using Ollama's hosted cloud
    models (https://ollama.com), for machines without enough local
    hardware to run larger models. Requires OLLAMA_CLOUD_API_KEY.

    Uses the same request/response shape as the local /api/generate
    endpoint since Ollama's cloud API is designed as a compatible surface.
    """

    name = "ollama_cloud"

    def __init__(self) -> None:
        self.base_url = settings.OLLAMA_CLOUD_BASE_URL
        self.api_key = settings.OLLAMA_CLOUD_API_KEY
        self.model = settings.OLLAMA_CLOUD_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT
        self.temperature = settings.OLLAMA_TEMPERATURE

    def is_available(self) -> bool:
        return bool(self.api_key)

    def generate(self, prompt: str, system: str = "", json_mode: bool = True) -> str:
        if not self.api_key:
            raise LLMUnavailableError("OLLAMA_CLOUD_API_KEY is not configured")

        if "qwen3" in self.model.lower():
            prompt = f"{prompt}\n\n/no_think"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": self.temperature, "num_predict": settings.OLLAMA_MAX_TOKENS},
        }
        if json_mode:
            payload["format"] = "json"

        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            resp = httpx.post(
                f"{self.base_url}/api/generate", json=payload, headers=headers, timeout=self.timeout
            )
        except httpx.TimeoutException as exc:
            raise LLMUnavailableError(f"Ollama Cloud request timed out after {self.timeout}s") from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(f"Ollama Cloud request failed: {exc}") from exc

        if resp.status_code == 401:
            raise LLMUnavailableError("Ollama Cloud rejected the API key (401)")
        if resp.status_code != 200:
            raise LLMUnavailableError(f"Ollama Cloud returned status {resp.status_code}: {resp.text[:200]}")

        try:
            data = resp.json()
        except ValueError as exc:
            raise LLMUnavailableError("Ollama Cloud returned malformed JSON envelope") from exc

        response_text = data.get("response", "")
        if not response_text:
            raise LLMUnavailableError("Ollama Cloud returned an empty response")
        return response_text
