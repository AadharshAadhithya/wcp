"""Stable event envelope for the Work Control Protocol."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from wcp.ids import is_ulid, new_ulid


class EntityType(StrEnum):
    QUESTION = "question"
    SESSION = "session"
    EXPERIMENT = "experiment"
    CLAIM = "claim"
    REVIEW = "review"


class ActorKind(StrEnum):
    HUMAN = "human"
    AGENT = "agent"
    SYSTEM = "system"


class Event(BaseModel):
    """Immutable semantic event accepted by the WCP store."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(default_factory=new_ulid)
    project_id: str
    entity_type: EntityType
    entity_id: str
    event_type: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor_id: str
    actor_kind: ActorKind
    session_id: str | None = None
    work_item_id: str | None = None
    evidence: tuple[str, ...] = ()
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str

    @field_validator("id", "project_id", "entity_id", "session_id")
    @classmethod
    def validate_wcp_ids(cls, value: str | None) -> str | None:
        if value is not None and not is_ulid(value):
            raise ValueError("WCP entity identifiers must be canonical ULIDs")
        return value

    @field_validator("event_type", "actor_id", "idempotency_key")
    @classmethod
    def validate_nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value


class StoredEvent(Event):
    sequence: int
