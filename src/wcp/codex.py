"""Codex JSONL stream adapter."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wcp.archive import SessionArchive
from wcp.events import ActorKind, EntityType
from wcp.workflow import Workflow


@dataclass(frozen=True, slots=True)
class IngestionResult:
    session_id: str
    event_count: int
    archive_path: Path
    checksum: str


class CodexStreamIngestor:
    def __init__(self, workflow: Workflow, archive: SessionArchive) -> None:
        self.workflow = workflow
        self.archive = archive

    def ingest(
        self,
        lines: Iterable[str],
        *,
        mode: str,
        actor_id: str = "agent:codex",
        question_id: str | None = None,
        echo: bool = False,
        successful: bool | Callable[[], bool] = True,
    ) -> IngestionResult:
        created = self.workflow.create(
            EntityType.SESSION,
            {
                "mode": mode,
                "driver": "codex",
                "question_id": question_id,
            },
            actor_id=actor_id,
            actor_kind=ActorKind.AGENT,
        )
        session_id = created.entity_id
        self.workflow.transition(
            EntityType.SESSION,
            session_id,
            "claimed",
            actor_id=actor_id,
            actor_kind=ActorKind.AGENT,
            session_id=session_id,
        )
        self.workflow.transition(
            EntityType.SESSION,
            session_id,
            "running",
            actor_id=actor_id,
            actor_kind=ActorKind.AGENT,
            session_id=session_id,
        )

        count = 0
        for raw_line in lines:
            if not raw_line.strip():
                continue
            try:
                codex_event: Any = json.loads(raw_line)
            except json.JSONDecodeError as error:
                codex_event = {
                    "type": "stream.parse_error",
                    "error": error.msg,
                    "raw": raw_line.rstrip("\n"),
                }
            canonical = json.dumps(codex_event, sort_keys=True, separators=(",", ":"))
            digest = hashlib.sha256(canonical.encode()).hexdigest()
            self.archive.append(session_id, canonical)
            self.workflow.record(
                EntityType.SESSION,
                session_id,
                {"last_codex_event": codex_event, "codex_event_count": count + 1},
                actor_id=actor_id,
                actor_kind=ActorKind.AGENT,
                session_id=session_id,
                idempotency_key=f"{session_id}:codex:{count}:{digest}",
            )
            count += 1
            if echo:
                print(raw_line.rstrip("\n"), flush=True)

        archive_path, checksum = self.archive.seal(session_id)
        did_succeed = successful() if callable(successful) else successful
        target = "completed" if did_succeed else "failed"
        self.workflow.transition(
            EntityType.SESSION,
            session_id,
            target,
            actor_id=actor_id,
            actor_kind=ActorKind.AGENT,
            session_id=session_id,
            data={
                "archive_path": str(archive_path),
                "archive_sha256": checksum,
                "codex_event_count": count,
            },
        )
        return IngestionResult(session_id, count, archive_path, checksum)
