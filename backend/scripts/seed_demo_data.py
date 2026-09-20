"""One-shot demo data seeding: creates an admin user and ingests all sample
logs directly against the database (no running server required).

Usage:
    python scripts/seed_demo_data.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, init_db  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.ingestion.log_ingestion import ingest_raw_log  # noqa: E402
from app.utils.security import hash_password  # noqa: E402

SAMPLE_LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "sample_logs"

DEMO_ADMIN_USERNAME = "admin"
DEMO_ADMIN_EMAIL = "admin@example.com"
DEMO_ADMIN_PASSWORD = "AdminPass123!"


def ensure_admin(db) -> None:
    existing = db.query(User).filter(User.username == DEMO_ADMIN_USERNAME).first()
    if existing:
        print(f"Admin user '{DEMO_ADMIN_USERNAME}' already exists.")
        return
    user = User(
        username=DEMO_ADMIN_USERNAME,
        email=DEMO_ADMIN_EMAIL,
        hashed_password=hash_password(DEMO_ADMIN_PASSWORD),
        role=UserRole.ADMIN.value,
    )
    db.add(user)
    db.commit()
    print(f"Created admin user: {DEMO_ADMIN_USERNAME} / {DEMO_ADMIN_PASSWORD}  (CHANGE THIS PASSWORD)")


def ingest_sample_logs(db) -> None:
    if not SAMPLE_LOGS_DIR.exists():
        print(f"Sample logs directory not found: {SAMPLE_LOGS_DIR}")
        return
    for path in sorted(SAMPLE_LOGS_DIR.glob("*.log")):
        content = path.read_text()
        result = ingest_raw_log(db, content=content, filename=path.name)
        print(
            f"  {path.name}: {result.events_created} events, "
            f"{result.alerts_created} alerts, {result.incidents_created} incidents"
        )


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        print("Ensuring demo admin user...")
        ensure_admin(db)
        print("Ingesting sample logs...")
        ingest_sample_logs(db)
        print("Demo data seeding complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
