import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    agents,
    alerts,
    auth,
    dashboard,
    health,
    incidents,
    investigations,
    llm_settings,
    logs,
    rag,
    reports,
    scans,
    threat_intel,
)
from app.config import get_settings
from app.database import init_db
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

_DEFAULT_SECRET_KEY = "dev-secret-key-change-in-production-please"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if os.environ.get("TESTING") != "1":
        if settings.DATABASE_URL.startswith("sqlite"):
            Path(settings.DATABASE_URL.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        init_db()
        if settings.ENVIRONMENT.lower() == "production" and settings.SECRET_KEY == _DEFAULT_SECRET_KEY:
            logger.warning("SECURITY: SECRET_KEY is still the default dev value - set a unique SECRET_KEY before real production use.")
        logger.info("%s started (env=%s)", settings.APP_NAME, settings.ENVIRONMENT)
    yield


app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(logs.router)
app.include_router(alerts.router)
app.include_router(incidents.router)
app.include_router(investigations.router)
app.include_router(agents.router)
app.include_router(dashboard.router)
app.include_router(rag.router)
app.include_router(threat_intel.router)
app.include_router(scans.router)
app.include_router(reports.router)
app.include_router(health.router)
app.include_router(llm_settings.router)


@app.get("/")
def root():
    return {"app": settings.APP_NAME, "status": "running", "docs": "/docs"}
