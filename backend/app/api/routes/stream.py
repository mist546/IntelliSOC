import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_current_user
from app.services.live_events import TICKET_TTL_SECONDS, broker, issue_stream_ticket, redeem_stream_ticket

router = APIRouter(prefix="/api/stream", tags=["stream"])

# A comment line is sent this often when nothing happens, so proxies and the
# browser keep the connection open and a dead connection is noticed.
KEEPALIVE_SECONDS = 15


def format_sse(message: dict) -> str:
    return f"data: {json.dumps(message, default=str)}\n\n"


@router.post("/ticket")
def create_stream_ticket(user=Depends(get_current_user)):
    return {"ticket": issue_stream_ticket(user.id), "expires_in": TICKET_TTL_SECONDS}


@router.get("")
async def stream_events(request: Request, ticket: str):
    if redeem_stream_ticket(ticket) is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired stream ticket")

    queue = broker.subscribe()

    async def event_source():
        try:
            yield "retry: 5000\n\n"
            yield format_sse({"type": "stream.connected", "data": {}})
            while not await request.is_disconnected():
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_SECONDS)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield format_sse(message)
        finally:
            broker.unsubscribe(queue)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
