from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_agent, get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.log_event import LogEvent
from app.schemas.agent import EventBatch
from app.schemas.log_event import LogEventCreate, LogEventOut, LogUploadResult
from app.services.ingestion.log_ingestion import ingest_normalized_events, ingest_raw_log
from app.utils.logging import get_logger
from app.utils.time import utc_now

router = APIRouter(prefix="/api", tags=["logs"])
logger = get_logger(__name__)
settings = get_settings()


@router.post("/logs/upload", response_model=LogUploadResult)
async def upload_log(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    allowed_ext = tuple(settings.ALLOWED_UPLOAD_EXTENSIONS)
    if not file.filename or not file.filename.lower().endswith(allowed_ext):
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {allowed_ext}")

    raw_bytes = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(raw_bytes) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")

    try:
        content = raw_bytes.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="Unable to decode file as text")

    result = ingest_raw_log(db, content=content, filename=file.filename)

    return LogUploadResult(
        filename=file.filename,
        source_type=result.source_type,
        events_created=result.events_created,
        alerts_created=result.alerts_created,
        incidents_created=result.incidents_created,
        parse_errors=result.parse_errors,
    )


@router.post("/events", status_code=status.HTTP_201_CREATED)
def ingest_events(
    batch: EventBatch,
    db: Session = Depends(get_db),
    agent=Depends(get_current_agent),
):
    events: list[LogEventCreate] = []
    for raw in batch.events:
        try:
            events.append(LogEventCreate(**raw))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=422, detail=f"Invalid event payload: {exc}")

    agent.last_seen_at = utc_now()
    result = ingest_normalized_events(db, events, agent_id=agent.id, default_source=agent.name)
    return {
        "events_created": result.events_created,
        "alerts_created": result.alerts_created,
        "incidents_created": result.incidents_created,
    }


@router.get("/logs", response_model=list[LogEventOut])
def list_logs(
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    source_ip: str | None = None,
    event_type: str | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
):
    query = db.query(LogEvent)
    if source_ip:
        query = query.filter(LogEvent.source_ip == source_ip)
    if event_type:
        query = query.filter(LogEvent.event_type == event_type)
    return query.order_by(LogEvent.timestamp.desc()).offset(skip).limit(limit).all()


@router.get("/logs/{log_id}", response_model=LogEventOut)
def get_log(log_id: str, db: Session = Depends(get_db), _user=Depends(get_current_user)):
    event = db.query(LogEvent).filter(LogEvent.id == log_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Log event not found")
    return event
