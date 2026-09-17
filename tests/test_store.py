from __future__ import annotations

from pathlib import Path

import pytest

from wcp.errors import IdempotencyConflict
from wcp.events import ActorKind, EntityType, Event
from wcp.reducers import InvalidTransition
from wcp.store import EventStore

PROJECT_ID = "00000000000000000000000000"
QUESTION_ID = "00000000000000000000000001"


def event(
    event_type: str,
    *,
    payload: dict[str, object] | None = None,
    key: str | None = None,
) -> Event:
    return Event(
        project_id=PROJECT_ID,
        entity_type=EntityType.QUESTION,
        entity_id=QUESTION_ID,
        event_type=event_type,
        actor_id="human:test",
        actor_kind=ActorKind.HUMAN,
        payload=payload or {},
        idempotency_key=key or event_type,
    )


def test_append_projects_state_and_is_idempotent(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "state.db")
    created = event(
        "question.created",
        payload={"key": "NR-RQ-001", "title": "Does it generalize?"},
    )

    first = store.append(created)
    duplicate = store.append(created.model_copy(update={"id": created.id}))
    transitioned = store.append(
        event("question.transitioned", payload={"to": "framing"})
    )

    aggregate = store.get(EntityType.QUESTION, QUESTION_ID)
    assert first.sequence == duplicate.sequence == 1
    assert transitioned.sequence == 2
    assert aggregate is not None
    assert aggregate["state"] == "framing"
    assert aggregate["version"] == 2
    assert len(store.events()) == 2


def test_invalid_transition_rolls_back_event(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "state.db")
    store.append(event("question.created"))

    with pytest.raises(InvalidTransition, match="Cannot transition"):
        store.append(event("question.transitioned", payload={"to": "settled"}))

    assert len(store.events()) == 1
    assert store.get("question", QUESTION_ID)["state"] == "proposed"


def test_first_event_must_create_aggregate(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "state.db")

    with pytest.raises(InvalidTransition, match="First question event"):
        store.append(event("question.transitioned", payload={"to": "framing"}))

    assert store.events() == []


def test_idempotency_key_cannot_hide_different_event(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "state.db")
    store.append(event("question.created", payload={"title": "Original"}, key="same"))

    with pytest.raises(IdempotencyConflict, match="different event"):
        store.append(
            event("question.created", payload={"title": "Changed"}, key="same")
        )

    assert len(store.events()) == 1
