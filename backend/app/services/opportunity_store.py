import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.services.search_service import normalize_url


APPLICATION_TRANSITIONS = {
    "interested": {"preparing", "withdrawn"},
    "preparing": {"submitted", "withdrawn"},
    "submitted": {"interview", "rejected", "withdrawn"},
    "interview": {"offered", "rejected", "withdrawn"},
    "offered": {"accepted", "rejected", "withdrawn"},
    "accepted": set(),
    "rejected": set(),
    "withdrawn": set(),
}

SCHEMA_VERSION = 1
MIGRATIONS = {
    1: (
        """CREATE TABLE IF NOT EXISTS opportunities (
            id TEXT PRIMARY KEY,
            canonical_key TEXT NOT NULL UNIQUE,
            title TEXT,
            organization TEXT,
            source_url TEXT NOT NULL,
            record_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            opportunity_id TEXT NOT NULL REFERENCES opportunities(id),
            status TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS application_status_events (
            id TEXT PRIMARY KEY,
            application_id TEXT NOT NULL REFERENCES applications(id),
            old_status TEXT,
            new_status TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            changed_at TEXT NOT NULL
        )""",
        "CREATE INDEX IF NOT EXISTS idx_applications_opportunity ON applications(opportunity_id)",
        "CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status)",
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_applications_opportunity ON applications(opportunity_id)",
    ),
}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class LocalOpportunityStore:
    """Small local SQLite store for reviewed opportunities and application history."""

    def __init__(self, path=None):
        configured = path or os.getenv("NEXORA_DB_PATH")
        self.path = Path(configured) if configured else (
            Path(__file__).resolve().parents[2] / "data" / "nexora.sqlite3"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self):
        with self._connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise RuntimeError(
                    f"Database schema version {version} is newer than supported "
                    f"version {SCHEMA_VERSION}. Upgrade NEXORA before opening this database."
                )
            while version < SCHEMA_VERSION:
                next_version = version + 1
                migration = MIGRATIONS.get(next_version)
                if migration is None:
                    raise RuntimeError(
                        f"No database migration is registered for version {next_version}."
                    )
                for statement in migration:
                    connection.execute(statement)
                connection.execute(f"PRAGMA user_version = {next_version}")
                version = next_version

    @staticmethod
    def _identity(record):
        source = record.get("source", {})
        extraction = record.get("extraction", {})
        source_url = normalize_url(source.get("url", ""))
        canonical_key = source_url or "|".join(
            str(extraction.get(field, "") or "").strip().casefold()
            for field in ("opportunity_title", "organization", "location")
        )
        if not canonical_key.strip("|"):
            canonical_key = hashlib.sha256(_json(record).encode("utf-8")).hexdigest()
        opportunity_id = hashlib.sha256(
            canonical_key.encode("utf-8")
        ).hexdigest()[:24]
        return opportunity_id, canonical_key, source_url

    def save_opportunity(self, record):
        opportunity_id, canonical_key, source_url = self._identity(record)
        extraction = record.get("extraction", {})
        timestamp = _now()
        with self._connect() as connection:
            connection.execute("""
                INSERT INTO opportunities
                    (id, canonical_key, title, organization, source_url,
                     record_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(canonical_key) DO UPDATE SET
                    title=excluded.title,
                    organization=excluded.organization,
                    source_url=excluded.source_url,
                    record_json=excluded.record_json,
                    updated_at=excluded.updated_at
            """, (
                opportunity_id,
                canonical_key,
                extraction.get("opportunity_title"),
                extraction.get("organization"),
                source_url or record.get("source", {}).get("url", ""),
                _json(record),
                timestamp,
                timestamp,
            ))
            stored = connection.execute(
                "SELECT id FROM opportunities WHERE canonical_key = ?",
                (canonical_key,),
            ).fetchone()
        return stored["id"]

    @staticmethod
    def _opportunity_row(row):
        if row is None:
            return None
        return {
            "opportunity_id": row["id"],
            "title": row["title"],
            "organization": row["organization"],
            "source_url": row["source_url"],
            **json.loads(row["record_json"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def get_opportunity(self, opportunity_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM opportunities WHERE id = ?",
                (opportunity_id,),
            ).fetchone()
        return self._opportunity_row(row)

    def list_opportunities(self, limit=50, offset=0):
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM opportunities ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self._opportunity_row(row) for row in rows]

    def create_application(self, opportunity_id, notes=""):
        application_id = None
        timestamp = _now()
        with self._connect() as connection:
            if not connection.execute(
                "SELECT 1 FROM opportunities WHERE id = ?", (opportunity_id,)
            ).fetchone():
                raise KeyError("Opportunity not found")
            existing = connection.execute(
                "SELECT id FROM applications WHERE opportunity_id = ?",
                (opportunity_id,),
            ).fetchone()
            if existing:
                application_id = existing["id"]
            else:
                application_id = uuid4().hex
                connection.execute("""
                    INSERT INTO applications
                        (id, opportunity_id, status, notes, created_at, updated_at)
                    VALUES (?, ?, 'interested', ?, ?, ?)
                """, (application_id, opportunity_id, notes, timestamp, timestamp))
                connection.execute("""
                    INSERT INTO application_status_events
                        (id, application_id, old_status, new_status, note, changed_at)
                    VALUES (?, ?, NULL, 'interested', ?, ?)
                """, (uuid4().hex, application_id, "Application tracking started", timestamp))
        return self.get_application(application_id)

    def get_application(self, application_id):
        with self._connect() as connection:
            row = connection.execute("""
                SELECT a.*, o.title AS opportunity_title,
                       o.organization AS opportunity_organization
                FROM applications a
                JOIN opportunities o ON o.id = a.opportunity_id
                WHERE a.id = ?
            """, (application_id,)).fetchone()
            events = connection.execute("""
                SELECT old_status, new_status, note, changed_at
                FROM application_status_events
                WHERE application_id = ? ORDER BY changed_at, id
            """, (application_id,)).fetchall()
        if row is None:
            return None
        result = dict(row)
        result["history"] = [dict(event) for event in events]
        return result

    def list_applications(self, limit=50, offset=0):
        with self._connect() as connection:
            ids = connection.execute(
                "SELECT id FROM applications ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
        return [self.get_application(row["id"]) for row in ids]

    def update_application(self, application_id, new_status, note=""):
        timestamp = _now()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status, notes FROM applications WHERE id = ?",
                (application_id,),
            ).fetchone()
            if row is None:
                raise KeyError("Application not found")
            old_status = row["status"]
            if new_status != old_status and new_status not in APPLICATION_TRANSITIONS[old_status]:
                raise ValueError(
                    f"Invalid application status transition: {old_status} -> {new_status}"
                )
            connection.execute(
                "UPDATE applications SET status = ?, notes = ?, updated_at = ? WHERE id = ?",
                (new_status, note or row["notes"], timestamp, application_id),
            )
            if new_status != old_status:
                connection.execute("""
                    INSERT INTO application_status_events
                        (id, application_id, old_status, new_status, note, changed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (uuid4().hex, application_id, old_status, new_status, note, timestamp))
        return self.get_application(application_id)
