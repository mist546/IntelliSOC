"""Real-time push of SOC activity to the dashboard (Server-Sent Events).

Anything in the backend can call `publish_event("alert.created", {...})`
after committing a change; every connected browser receives the message
over GET /api/stream within milliseconds and refreshes the affected views.

This is a deliberately small, in-process publish/subscribe broker: one
asyncio.Queue per connected browser. Publishers are usually sync route
handlers or background jobs running in worker threads, so messages are
handed to each subscriber's event loop with `call_soon_threadsafe`. It
works for a single backend process (how this project runs); scaling to
several processes would need an external broker such as Redis pub/sub.

Browsers' EventSource API cannot send an Authorization header, so the
stream is authenticated with a short-lived, single-use ticket obtained
via an authenticated POST (the JWT itself never appears in a URL/log).
"""
import asyncio
import secrets
import threading
import time

from app.utils.logging import get_logger
from app.utils.time import utc_now

logger = get_logger(__name__)

# Per-browser backlog. A client that falls this far behind only misses
# refresh hints (it re-fetches data anyway), so the oldest are dropped.
QUEUE_SIZE = 200
TICKET_TTL_SECONDS = 30


def _offer(queue: asyncio.Queue, message: dict) -> None:
    if queue.full():
        queue.get_nowait()
    queue.put_nowait(message)


class LiveEventBroker:
    def __init__(self) -> None:
        self._subscribers: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = []
        self._lock = threading.Lock()

    def subscribe(self) -> asyncio.Queue:
        """Must be called from inside the event loop that will read the queue."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
        with self._lock:
            self._subscribers.append((asyncio.get_running_loop(), queue))
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        with self._lock:
            self._subscribers = [(loop, q) for loop, q in self._subscribers if q is not queue]

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)

    def publish(self, event_type: str, data: dict) -> None:
        message = {"type": event_type, "data": data, "timestamp": utc_now().isoformat()}
        with self._lock:
            subscribers = list(self._subscribers)
        for loop, queue in subscribers:
            try:
                loop.call_soon_threadsafe(_offer, queue, message)
            except RuntimeError:  # that subscriber's loop has already closed
                self.unsubscribe(queue)


broker = LiveEventBroker()


def publish_event(event_type: str, data: dict) -> None:
    """Never raises: a live-update failure must not break ingestion or investigations."""
    try:
        broker.publish(event_type, data)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to publish live event %s", event_type)


# ---- stream tickets ---------------------------------------------------------

_tickets: dict[str, tuple[str, float]] = {}
_tickets_lock = threading.Lock()


def issue_stream_ticket(user_id: str) -> str:
    ticket = secrets.token_urlsafe(24)
    now = time.monotonic()
    with _tickets_lock:
        for key in [k for k, (_, expires) in _tickets.items() if expires < now]:
            del _tickets[key]
        _tickets[ticket] = (user_id, now + TICKET_TTL_SECONDS)
    return ticket


def redeem_stream_ticket(ticket: str) -> str | None:
    """Returns the user id if the ticket is valid; a ticket works only once."""
    with _tickets_lock:
        entry = _tickets.pop(ticket, None)
    if entry is None or entry[1] < time.monotonic():
        return None
    return entry[0]
