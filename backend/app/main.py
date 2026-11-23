import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    agents,
    ai,
    alerts,
    auth,
    dashboard,
    health,
    incidents,
    investigations,
    knowledge,
    llm_settings,
    logs,
    rag,
    reports,
    scans,
    stream,
    threat_intel,
)
from app.config import get_settings
from app.database import init_db
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

_DEFAULT_SECRET_KEY = "dev-secret-key-change-in-production-please"


def _fail_interrupted_investigations() -> None:
    """Investigations run in the background; any still RUNNING at startup
    were cut off by the previous shutdown and will never finish."""
    from app.database.session import SessionLocal
    from app.models.investigation import Investigation

    db = SessionLocal()
    try:
        interrupted = db.query(Investigation).filter(Investigation.status.in_(["PENDING", "RUNNING"])).all()
        for investigation in interrupted:
            investigation.status = "FAILED"
            investigation.error_message = "Interrupted by a backend restart before it finished. Start a new investigation."
        if interrupted:
            db.commit()
            logger.info("Marked %d interrupted investigation(s) as FAILED", len(interrupted))
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if os.environ.get("TESTING") != "1":
        if settings.DATABASE_URL.startswith("sqlite"):
            Path(settings.DATABASE_URL.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        init_db()
        _fail_interrupted_investigations()
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
app.include_router(knowledge.router)
app.include_router(threat_intel.router)
app.include_router(scans.router)
app.include_router(reports.router)
app.include_router(health.router)
app.include_router(llm_settings.router)
app.include_router(ai.router)
app.include_router(stream.router)


@app.get("/")
def root():
    return {"app": settings.APP_NAME, "status": "running", "docs": "/docs"}
