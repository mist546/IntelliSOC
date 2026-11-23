from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db

router = APIRouter(prefix="/api", tags=["health"])
settings = get_settings()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    checks = {"database": "unknown", "ollama": "unknown"}

    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc}"

    # Probe whichever route the active provider uses. Only the direct
    # ollama.com API (cloud provider with a REST key) skips the local daemon.
    if settings.LLM_PROVIDER == "ollama_cloud" and settings.OLLAMA_CLOUD_API_KEY:
        checks["ollama"] = "ok"
    else:
        try:
            import httpx

            resp = httpx.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=3)
            if resp.status_code != 200:
                checks["ollama"] = f"error: status {resp.status_code}"
            else:
                model = settings.OLLAMA_CLOUD_MODEL if settings.LLM_PROVIDER == "ollama_cloud" else settings.OLLAMA_MODEL
                wanted = model if ":" in model else f"{model}:latest"
                installed = {m.get("name", "") for m in resp.json().get("models", [])}
                checks["ollama"] = "ok" if wanted in installed else f"error: model '{model}' not available - run: ollama pull {model}"
        except Exception as exc:  # noqa: BLE001
            checks["ollama"] = f"unavailable: {exc}"

    overall = "ok" if checks["database"] == "ok" else "degraded"
    return {"status": overall, "checks": checks, "app": settings.APP_NAME}
