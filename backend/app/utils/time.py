from datetime import datetime, timezone


def utc_now() -> datetime:
    """Current UTC time as a naive datetime.

    SQLite has no native timezone-aware storage: SQLAlchemy silently loses
    tzinfo on any value re-read from the database after the ORM identity
    map expires (e.g. after a commit), while freshly-constructed Python
    objects in the same process keep whatever tzinfo they were given. Mixing
    the two raises `TypeError: can't compare offset-naive and offset-aware
    datetimes` the moment two such values are compared - which happens in
    practice as soon as a second request/ingestion touches rows committed
    by an earlier one. The project-wide convention is therefore: every
    datetime that is stored in, or compared against, a database column is
    naive and implicitly UTC. Use this helper (not datetime.now(timezone.utc)
    or the deprecated datetime.utcnow()) wherever such a value is produced.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_naive_utc(dt: datetime | None) -> datetime | None:
    """Normalize any datetime (naive-assumed-UTC or timezone-aware) to a
    naive UTC datetime, per this project's convention (see utc_now() above).
    Useful for values received from outside the process - e.g. an ISO8601
    timestamp with an offset submitted by the endpoint agent - which may
    arrive timezone-aware.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt
