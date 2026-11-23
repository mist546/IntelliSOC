from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user, require_admin
from app.config import BASE_DIR, get_settings
from app.schemas.llm_settings import LLMSettingsOut, LLMSettingsUpdate
from app.utils.env_file import update_env_file
from app.utils.logging import get_logger

router = APIRouter(prefix="/api/settings/llm", tags=["settings"])
logger = get_logger(__name__)

VALID_PROVIDERS = {"ollama_local", "ollama_cloud"}


def _status_out() -> LLMSettingsOut:
    from app.services.llm.service import is_llm_available

    settings = get_settings()
    return LLMSettingsOut(
        provider=settings.LLM_PROVIDER,
        ollama_model=settings.OLLAMA_MODEL,
        ollama_base_url=settings.OLLAMA_BASE_URL,
        ollama_cloud_model=settings.OLLAMA_CLOUD_MODEL,
        ollama_cloud_base_url=settings.OLLAMA_CLOUD_BASE_URL,
        ollama_cloud_api_key_configured=bool(settings.OLLAMA_CLOUD_API_KEY),
        reachable=is_llm_available(),
    )


@router.get("", response_model=LLMSettingsOut)
def get_llm_settings(_user=Depends(get_current_user)):
    return _status_out()


@router.patch("", response_model=LLMSettingsOut)
def update_llm_settings(payload: LLMSettingsUpdate, _admin=Depends(require_admin)):
    settings = get_settings()

    if payload.provider is not None and payload.provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"provider must be one of {sorted(VALID_PROVIDERS)}")

    env_updates: dict[str, str] = {}

    if payload.provider is not None:
        settings.LLM_PROVIDER = payload.provider
        env_updates["LLM_PROVIDER"] = payload.provider

    if payload.ollama_model is not None:
        settings.OLLAMA_MODEL = payload.ollama_model
        env_updates["OLLAMA_MODEL"] = payload.ollama_model

    if payload.ollama_base_url is not None:
        settings.OLLAMA_BASE_URL = payload.ollama_base_url
        env_updates["OLLAMA_BASE_URL"] = payload.ollama_base_url

    if payload.ollama_cloud_model is not None:
        settings.OLLAMA_CLOUD_MODEL = payload.ollama_cloud_model
        env_updates["OLLAMA_CLOUD_MODEL"] = payload.ollama_cloud_model

    if payload.ollama_cloud_base_url is not None:
        settings.OLLAMA_CLOUD_BASE_URL = payload.ollama_cloud_base_url
        env_updates["OLLAMA_CLOUD_BASE_URL"] = payload.ollama_cloud_base_url

    if payload.ollama_cloud_api_key is not None:
        settings.OLLAMA_CLOUD_API_KEY = payload.ollama_cloud_api_key
        env_updates["OLLAMA_CLOUD_API_KEY"] = payload.ollama_cloud_api_key

    if env_updates:
        try:
            update_env_file(BASE_DIR / ".env", env_updates)
        except OSError as exc:
            logger.warning("Could not persist LLM settings to .env: %s", exc)

    return _status_out()
