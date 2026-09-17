"""SQLite event store and synchronous aggregate projection."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from wcp.errors import IdempotencyConflict
from wcp.events import Event, StoredEvent
from wcp.reducers import reduce_event

SCHEMA = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    project_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    actor_kind TEXT NOT NULL,
    session_id TEXT,
    work_item_id TEXT,
    evidence_json TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS events_entity_sequence
ON events(entity_type, entity_id, sequence);

CREATE TABLE IF NOT EXISTS aggregates (
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    state TEXT NOT NULL,
    version INTEGER NOT NULL,
    document_json TEXT NOT NULL,
    last_event_id TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS external_refs (
    provider TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    external_id TEXT NOT NULL,
    external_url TEXT,
    metadata_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provider, entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS external_events (
    provider TEXT NOT NULL,
    event_id TEXT NOT NULL,
    external_id TEXT,
    projected_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provider, event_id)
);
"""


class EventStore:
    """Append-only event store with atomic, deterministic projections."""

    def __init__(self, path: Path) -> None:
        self.path = path.expanduser().resolve()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self._connection() as connection:
            connection.executescript(SCHEMA)
            connection.commit()

    def append(self, event: Event) -> StoredEvent:
        """Append once and update the aggregate in the same transaction."""

        self.initialize()
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            duplicate = connection.execute(
                "SELECT * FROM events WHERE idempotency_key = ?",
                (event.idempotency_key,),
            ).fetchone()
            if duplicate is not None:
                stored = self._stored_event(duplicate)
                connection.rollback()
                comparable_fields = (
                    "project_id",
                    "entity_type",
                    "entity_id",
                    "event_type",
                    "actor_id",
                    "actor_kind",
                    "session_id",
                    "work_item_id",
                    "evidence",
                    "payload",
                )
                if any(
                    getattr(stored, field) != getattr(event, field)
                    for field in comparable_fields
                ):
                    raise IdempotencyConflict(
                        f"Idempotency key {event.idempotency_key!r} was already used "
                        "for a different event"
                    )
                return stored

            row = connection.execute(
                "SELECT document_json FROM aggregates "
                "WHERE entity_type = ? AND entity_id = ?",
                (event.entity_type.value, event.entity_id),
            ).fetchone()
            current = json.loads(row["document_json"]) if row else None
            projected = reduce_event(current, event)

            cursor = connection.execute(
                """
                INSERT INTO events (
                    id, project_id, entity_type, entity_id, event_type,
                    occurred_at, actor_id, actor_kind, session_id, work_item_id,
                    evidence_json, payload_json, idempotency_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.project_id,
                    event.entity_type.value,
                    event.entity_id,
                    event.event_type,
                    event.occurred_at.isoformat(),
                    event.actor_id,
                    event.actor_kind.value,
                    event.session_id,
                    event.work_item_id,
                    json.dumps(event.evidence, separators=(",", ":")),
                    json.dumps(event.payload, sort_keys=True, separators=(",", ":")),
                    event.idempotency_key,
                ),
            )
            connection.execute(
                """
                INSERT INTO aggregates (
                    entity_type, entity_id, project_id, state, version,
                    document_json, last_event_id, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_type, entity_id) DO UPDATE SET
                    state = excluded.state,
                    version = excluded.version,
                    document_json = excluded.document_json,
                    last_event_id = excluded.last_event_id,
                    updated_at = excluded.updated_at
                """,
                (
                    event.entity_type.value,
                    event.entity_id,
                    event.project_id,
                    projected["state"],
                    projected["version"],
                    json.dumps(projected, sort_keys=True, separators=(",", ":")),
                    event.id,
                    projected["updated_at"],
                ),
            )
            connection.commit()
            return StoredEvent(**event.model_dump(), sequence=cursor.lastrowid)

    def get(self, entity_type: str, entity_id: str) -> dict[str, Any] | None:
        self.initialize()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT document_json FROM aggregates "
                "WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id),
            ).fetchone()
        return json.loads(row["document_json"]) if row else None

    def list(self, entity_type: str, project_id: str) -> list[dict[str, Any]]:
        self.initialize()
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT document_json FROM aggregates "
                "WHERE entity_type = ? AND project_id = ? ORDER BY updated_at",
                (entity_type, project_id),
            ).fetchall()
        return [json.loads(row["document_json"]) for row in rows]

    def events(self, after_sequence: int = 0) -> list[StoredEvent]:
        self.initialize()
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM events WHERE sequence > ? ORDER BY sequence",
                (after_sequence,),
            ).fetchall()
        return [self._stored_event(row) for row in rows]

    def external_ref(
        self, provider: str, entity_type: str, entity_id: str
    ) -> dict[str, Any] | None:
        self.initialize()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM external_refs WHERE provider = ? "
                "AND entity_type = ? AND entity_id = ?",
                (provider, entity_type, entity_id),
            ).fetchone()
        if row is None:
            return None
        return {
            "external_id": row["external_id"],
            "external_url": row["external_url"],
            "metadata": json.loads(row["metadata_json"]),
        }

    def link_external(
        self,
        provider: str,
        entity_type: str,
        entity_id: str,
        external_id: str,
        *,
        external_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.initialize()
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO external_refs (
                    provider, entity_type, entity_id, external_id,
                    external_url, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(provider, entity_type, entity_id) DO UPDATE SET
                    external_id = excluded.external_id,
                    external_url = excluded.external_url,
                    metadata_json = excluded.metadata_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    provider,
                    entity_type,
                    entity_id,
                    external_id,
                    external_url,
                    json.dumps(metadata or {}, sort_keys=True),
                ),
            )
            connection.commit()

    def event_was_projected(self, provider: str, event_id: str) -> bool:
        self.initialize()
        with self._connection() as connection:
            row = connection.execute(
                "SELECT 1 FROM external_events WHERE provider = ? AND event_id = ?",
                (provider, event_id),
            ).fetchone()
        return row is not None

    def mark_event_projected(
        self, provider: str, event_id: str, external_id: str | None = None
    ) -> None:
        self.initialize()
        with self._connection() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO external_events "
                "(provider, event_id, external_id) VALUES (?, ?, ?)",
                (provider, event_id, external_id),
            )
            connection.commit()

    @staticmethod
    def _stored_event(row: sqlite3.Row) -> StoredEvent:
        return StoredEvent(
            sequence=row["sequence"],
            id=row["id"],
            project_id=row["project_id"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            event_type=row["event_type"],
            occurred_at=row["occurred_at"],
            actor_id=row["actor_id"],
            actor_kind=row["actor_kind"],
            session_id=row["session_id"],
            work_item_id=row["work_item_id"],
            evidence=tuple(json.loads(row["evidence_json"])),
            payload=json.loads(row["payload_json"]),
            idempotency_key=row["idempotency_key"],
        )
