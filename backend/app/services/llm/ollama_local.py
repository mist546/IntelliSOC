import httpx

from app.config import get_settings
from app.services.llm.base import LLMProvider, LLMUnavailableError
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class OllamaLocalProvider(LLMProvider):
    name = "ollama_local"

    def __init__(self) -> None:
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.timeout = settings.OLLAMA_TIMEOUT
        self.temperature = settings.OLLAMA_TEMPERATURE

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code != 200:
                return False
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            return any(self.model.split(":")[0] in m for m in models)
        except httpx.HTTPError:
            return False

    def generate(self, prompt: str, system: str = "", json_mode: bool = True) -> str:
        # Qwen3 models support a literal "/no_think" directive to skip their
        # (slow, verbose) extended-reasoning mode, which matters a lot on
        # CPU-only hardware. Harmless no-op for other model families.
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

        try:
            resp = httpx.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
        except httpx.TimeoutException as exc:
            raise LLMUnavailableError(f"Ollama request timed out after {self.timeout}s") from exc
        except httpx.ConnectError as exc:
            raise LLMUnavailableError(f"Could not connect to Ollama at {self.base_url}") from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailableError(f"Ollama request failed: {exc}") from exc

        if resp.status_code == 404:
            raise LLMUnavailableError(f"Model '{self.model}' not found. Run: ollama pull {self.model}")
        if resp.status_code != 200:
            raise LLMUnavailableError(f"Ollama returned status {resp.status_code}: {resp.text[:200]}")

        try:
            data = resp.json()
        except ValueError as exc:
            raise LLMUnavailableError("Ollama returned malformed JSON envelope") from exc

        response_text = data.get("response", "")
        if not response_text:
            raise LLMUnavailableError("Ollama returned an empty response")
        return response_text
