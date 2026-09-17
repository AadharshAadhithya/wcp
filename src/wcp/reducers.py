"""Pure deterministic reducers for WCP aggregate state."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from wcp.errors import WcpError
from wcp.events import EntityType, Event


class InvalidTransition(WcpError):
    """Raised when an event violates an aggregate state machine."""


INITIAL_STATES: dict[EntityType, str] = {
    EntityType.QUESTION: "proposed",
    EntityType.SESSION: "queued",
    EntityType.EXPERIMENT: "planned",
    EntityType.CLAIM: "proposed",
    EntityType.REVIEW: "pending",
}

TRANSITIONS: dict[EntityType, dict[str, set[str]]] = {
    EntityType.QUESTION: {
        "proposed": {"framing", "abandoned", "superseded"},
        "framing": {"ready", "abandoned", "superseded"},
        "ready": {"investigating", "abandoned", "superseded"},
        "investigating": {"awaiting-analysis", "abandoned", "superseded"},
        "awaiting-analysis": {"awaiting-decision", "investigating"},
        "awaiting-decision": {"settled", "investigating"},
        "settled": {"framing"},
        "abandoned": set(),
        "superseded": set(),
    },
    EntityType.SESSION: {
        "queued": {"claimed", "interrupted", "failed"},
        "claimed": {"running", "interrupted", "failed"},
        "running": {"waiting", "completed", "interrupted", "failed"},
        "waiting": {"running", "completed", "interrupted", "failed"},
        "completed": set(),
        "interrupted": set(),
        "failed": set(),
    },
    EntityType.EXPERIMENT: {
        "planned": {"launched", "cancelled"},
        "launched": {"running", "failed", "cancelled"},
        "running": {"succeeded", "failed", "cancelled"},
        "succeeded": {"analyzed"},
        "failed": {"analyzed"},
        "cancelled": set(),
        "analyzed": set(),
    },
    EntityType.CLAIM: {
        "proposed": {"pending-review"},
        "pending-review": {"accepted", "rejected", "superseded"},
        "accepted": {"superseded"},
        "rejected": set(),
        "superseded": set(),
    },
    EntityType.REVIEW: {
        "pending": {"accepted", "rejected", "deferred", "superseded"},
        "deferred": {"pending", "superseded"},
        "accepted": set(),
        "rejected": set(),
        "superseded": set(),
    },
}


def reduce_event(current: dict[str, Any] | None, event: Event) -> dict[str, Any]:
    """Apply one event to aggregate state without side effects."""

    created_type = f"{event.entity_type.value}.created"
    transitioned_type = f"{event.entity_type.value}.transitioned"
    recorded_type = f"{event.entity_type.value}.recorded"

    if current is None:
        if event.event_type != created_type:
            raise InvalidTransition(
                f"First {event.entity_type.value} event must be {created_type!r}"
            )
        return {
            "id": event.entity_id,
            "entity_type": event.entity_type.value,
            "project_id": event.project_id,
            "state": INITIAL_STATES[event.entity_type],
            "data": deepcopy(event.payload),
            "version": 1,
            "last_event_id": event.id,
            "updated_at": event.occurred_at.isoformat(),
        }

    state = deepcopy(current)
    if event.event_type == created_type:
        raise InvalidTransition(f"{event.entity_type.value} already exists")
    if event.event_type == transitioned_type:
        target = event.payload.get("to")
        if not isinstance(target, str):
            raise InvalidTransition("transition event requires a string payload.to")
        allowed = TRANSITIONS[event.entity_type].get(state["state"], set())
        if target not in allowed:
            raise InvalidTransition(
                f"Cannot transition {event.entity_type.value} from "
                f"{state['state']!r} to {target!r}"
            )
        state["state"] = target
        transition_data = event.payload.get("data")
        if transition_data is not None:
            if not isinstance(transition_data, dict):
                raise InvalidTransition("transition payload.data must be an object")
            state["data"].update(deepcopy(transition_data))
    elif event.event_type == recorded_type:
        state["data"].update(deepcopy(event.payload))
    else:
        raise InvalidTransition(
            f"Unsupported event type {event.event_type!r} for {event.entity_type.value}"
        )

    state["version"] += 1
    state["last_event_id"] = event.id
    state["updated_at"] = event.occurred_at.isoformat()
    return state
