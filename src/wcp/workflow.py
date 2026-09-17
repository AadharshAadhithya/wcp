"""Application service for recording semantic workflow operations."""

from __future__ import annotations

from typing import Any

from wcp.events import ActorKind, EntityType, Event, StoredEvent
from wcp.ids import new_ulid
from wcp.store import EventStore


class Workflow:
    def __init__(self, store: EventStore, project_id: str) -> None:
        self.store = store
        self.project_id = project_id

    def create(
        self,
        entity_type: EntityType,
        data: dict[str, Any],
        *,
        actor_id: str,
        actor_kind: ActorKind,
        entity_id: str | None = None,
        session_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> StoredEvent:
        entity_id = entity_id or new_ulid()
        return self.store.append(
            Event(
                project_id=self.project_id,
                entity_type=entity_type,
                entity_id=entity_id,
                event_type=f"{entity_type.value}.created",
                actor_id=actor_id,
                actor_kind=actor_kind,
                session_id=session_id,
                payload=data,
                idempotency_key=idempotency_key or f"{entity_id}:created",
            )
        )

    def transition(
        self,
        entity_type: EntityType,
        entity_id: str,
        target: str,
        *,
        actor_id: str,
        actor_kind: ActorKind,
        data: dict[str, Any] | None = None,
        session_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> StoredEvent:
        if (
            entity_type is EntityType.CLAIM
            and target in {"accepted", "rejected"}
            and actor_kind is not ActorKind.HUMAN
        ):
            raise ValueError("Only a human actor may accept or reject a claim")
        if (
            entity_type is EntityType.QUESTION
            and target == "settled"
            and actor_kind is not ActorKind.HUMAN
        ):
            raise ValueError("Only a human actor may settle a research question")
        return self.store.append(
            Event(
                project_id=self.project_id,
                entity_type=entity_type,
                entity_id=entity_id,
                event_type=f"{entity_type.value}.transitioned",
                actor_id=actor_id,
                actor_kind=actor_kind,
                session_id=session_id,
                payload={"to": target, "data": data or {}},
                idempotency_key=idempotency_key or new_ulid(),
            )
        )

    def record(
        self,
        entity_type: EntityType,
        entity_id: str,
        data: dict[str, Any],
        *,
        actor_id: str,
        actor_kind: ActorKind,
        session_id: str | None = None,
        evidence: tuple[str, ...] = (),
        idempotency_key: str | None = None,
    ) -> StoredEvent:
        return self.store.append(
            Event(
                project_id=self.project_id,
                entity_type=entity_type,
                entity_id=entity_id,
                event_type=f"{entity_type.value}.recorded",
                actor_id=actor_id,
                actor_kind=actor_kind,
                session_id=session_id,
                evidence=evidence,
                payload=data,
                idempotency_key=idempotency_key or new_ulid(),
            )
        )
