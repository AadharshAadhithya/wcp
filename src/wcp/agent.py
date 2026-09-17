"""Agent-facing semantic operations shared by MCP and future harness adapters."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from wcp.events import ActorKind, EntityType
from wcp.manifest import load_manifest
from wcp.project import MANIFEST_RELATIVE_PATH
from wcp.runtime import database_path
from wcp.store import EventStore
from wcp.workflow import Workflow


class AgentTools:
    def __init__(self, workflow: Workflow, actor_id: str = "agent:codex") -> None:
        self.workflow = workflow
        self.actor_id = actor_id

    @classmethod
    def from_project(
        cls,
        project_path: Path,
        *,
        actor_id: str = "agent:codex",
        db_path: Path | None = None,
    ) -> AgentTools:
        root = project_path.expanduser().resolve()
        manifest = load_manifest(root / MANIFEST_RELATIVE_PATH)
        store = EventStore(database_path(manifest.project.id, db_path))
        return cls(Workflow(store, manifest.project.id), actor_id)

    def project_context(self) -> dict[str, Any]:
        return {
            "project_id": self.workflow.project_id,
            "actor_id": self.actor_id,
            "capabilities": [
                "create entity",
                "record semantic data and evidence",
                "request non-human lifecycle transitions",
                "read projected state",
            ],
            "human_only": [
                "accept or reject claims",
                "accept or reject reviews",
                "settle research questions",
            ],
        }

    def create_entity(
        self,
        entity_type: str,
        data: dict[str, Any],
        *,
        session_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        kind = EntityType(entity_type)
        event = self.workflow.create(
            kind,
            data,
            actor_id=self.actor_id,
            actor_kind=ActorKind.AGENT,
            session_id=session_id,
            idempotency_key=idempotency_key,
        )
        return self.workflow.store.get(kind.value, event.entity_id) or {}

    def transition_entity(
        self,
        entity_type: str,
        entity_id: str,
        target: str,
        *,
        data: dict[str, Any] | None = None,
        session_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        kind = EntityType(entity_type)
        self.workflow.transition(
            kind,
            entity_id,
            target,
            actor_id=self.actor_id,
            actor_kind=ActorKind.AGENT,
            data=data,
            session_id=session_id,
            idempotency_key=idempotency_key,
        )
        return self.workflow.store.get(kind.value, entity_id) or {}

    def record_entity(
        self,
        entity_type: str,
        entity_id: str,
        data: dict[str, Any],
        *,
        evidence: list[str] | None = None,
        session_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        kind = EntityType(entity_type)
        self.workflow.record(
            kind,
            entity_id,
            data,
            actor_id=self.actor_id,
            actor_kind=ActorKind.AGENT,
            session_id=session_id,
            evidence=tuple(evidence or []),
            idempotency_key=idempotency_key,
        )
        return self.workflow.store.get(kind.value, entity_id) or {}

    def get_entity(self, entity_type: str, entity_id: str) -> dict[str, Any]:
        result = self.workflow.store.get(EntityType(entity_type).value, entity_id)
        if result is None:
            raise ValueError(f"No {entity_type} {entity_id}")
        return result

    def list_entities(self, entity_type: str) -> list[dict[str, Any]]:
        return self.workflow.store.list(
            EntityType(entity_type).value, self.workflow.project_id
        )
