from __future__ import annotations

from pathlib import Path
from typing import Any

from wcp.events import ActorKind, EntityType
from wcp.plane import PlaneProjector
from wcp.store import EventStore
from wcp.workflow import Workflow

PROJECT_ID = "00000000000000000000000000"


class FakePlane:
    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []
        self.updated: list[tuple[str, dict[str, Any]]] = []
        self.comments: list[tuple[str, dict[str, Any]]] = []

    def list_states(self) -> list[dict[str, Any]]:
        return [
            {"id": "state-backlog", "name": "Backlog", "group": "backlog"},
            {"id": "state-unstarted", "name": "Todo", "group": "unstarted"},
            {"id": "state-started", "name": "In Progress", "group": "started"},
        ]

    def create_work_item(self, data: dict[str, Any]) -> dict[str, Any]:
        self.created.append(data)
        return {"id": f"work-{len(self.created)}", "sequence_id": len(self.created)}

    def update_work_item(
        self, work_item_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        self.updated.append((work_item_id, data))
        return {"id": work_item_id}

    def create_comment(self, work_item_id: str, data: dict[str, Any]) -> dict[str, Any]:
        self.comments.append((work_item_id, data))
        return {"id": f"comment-{len(self.comments)}"}


def test_plane_projection_is_idempotent_and_links_experiment(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "state.db")
    workflow = Workflow(store, PROJECT_ID)
    question = workflow.create(
        EntityType.QUESTION,
        {"key": "NR-RQ-001", "title": "Generalization"},
        actor_id="human:owner",
        actor_kind=ActorKind.HUMAN,
    )
    experiment = workflow.create(
        EntityType.EXPERIMENT,
        {
            "key": "NR-EXP-001",
            "title": "Unseen channel",
            "question_id": question.entity_id,
        },
        actor_id="human:owner",
        actor_kind=ActorKind.HUMAN,
    )
    workflow.transition(
        EntityType.QUESTION,
        question.entity_id,
        "framing",
        actor_id="human:owner",
        actor_kind=ActorKind.HUMAN,
    )
    client = FakePlane()
    projector = PlaneProjector(client)

    first = projector.sync(store, PROJECT_ID)
    second = projector.sync(store, PROJECT_ID)

    assert first == {"created": 2, "updated": 0, "comments": 1}
    assert second == {"created": 0, "updated": 2, "comments": 0}
    assert client.created[1]["parent"] == "work-1"
    assert client.created[0]["state"] == "state-unstarted"
    assert (
        store.external_ref("plane", "experiment", experiment.entity_id)["external_id"]
        == "work-2"
    )
