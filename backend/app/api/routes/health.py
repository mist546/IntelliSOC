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

    try:
        import httpx

        resp = httpx.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=3)
        checks["ollama"] = "ok" if resp.status_code == 200 else f"error: status {resp.status_code}"
    except Exception as exc:  # noqa: BLE001
        checks["ollama"] = f"unavailable: {exc}"

    overall = "ok" if checks["database"] == "ok" else "degraded"
    return {"status": overall, "checks": checks, "app": settings.APP_NAME}
