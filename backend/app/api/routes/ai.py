from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.config import get_settings
from app.schemas.llm_settings import AIStatusOut

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/status", response_model=AIStatusOut)
def ai_status(_user=Depends(get_current_user)):
    from app.services.llm.service import is_llm_available

    settings = get_settings()
    model = settings.OLLAMA_CLOUD_MODEL if settings.LLM_PROVIDER == "ollama_cloud" else settings.OLLAMA_MODEL
    return AIStatusOut(
        provider=settings.LLM_PROVIDER,
        model=model,
        embedding_model=settings.OLLAMA_EMBED_MODEL,
        reachable=is_llm_available(),
    )
