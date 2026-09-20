class LLMUnavailableError(Exception):
    """Raised whenever the configured LLM provider cannot produce a response
    (connection error, timeout, missing model, non-2xx response). Callers
    must catch this and degrade gracefully rather than crash the
    investigation.
    """


class LLMProvider:
    name = "base"

    def generate(self, prompt: str, system: str = "", json_mode: bool = True) -> str:
        raise NotImplementedError

    def is_available(self) -> bool:
        raise NotImplementedError
