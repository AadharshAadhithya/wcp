from pathlib import Path

import pytest

from wcp.events import ActorKind, EntityType
from wcp.store import EventStore
from wcp.workflow import Workflow, WorkflowGuardError

PROJECT_ID = "00000000000000000000000000"


def test_only_human_can_accept_claim(tmp_path: Path) -> None:
    workflow = Workflow(EventStore(tmp_path / "state.db"), PROJECT_ID)
    created = workflow.create(
        EntityType.CLAIM,
        {
            "title": "A claim",
            "exact_scope": "One test condition",
            "supporting_evidence": ["run:1"],
            "confidence": "moderate",
            "limitations": ["single seed"],
        },
        actor_id="agent:test",
        actor_kind=ActorKind.AGENT,
    )
    workflow.transition(
        EntityType.CLAIM,
        created.entity_id,
        "pending-review",
        actor_id="agent:test",
        actor_kind=ActorKind.AGENT,
    )

    with pytest.raises(ValueError, match="Only a human"):
        workflow.transition(
            EntityType.CLAIM,
            created.entity_id,
            "accepted",
            actor_id="agent:test",
            actor_kind=ActorKind.AGENT,
        )

    workflow.transition(
        EntityType.CLAIM,
        created.entity_id,
        "accepted",
        actor_id="human:owner",
        actor_kind=ActorKind.HUMAN,
    )
    assert workflow.store.get("claim", created.entity_id)["state"] == "accepted"


def test_question_requires_complete_evidence_and_accepted_claim(tmp_path: Path) -> None:
    workflow = Workflow(EventStore(tmp_path / "state.db"), PROJECT_ID)
    question = workflow.create(
        EntityType.QUESTION,
        {"title": "Question"},
        actor_id="human:owner",
        actor_kind=ActorKind.HUMAN,
    )
    for state in (
        "framing",
        "ready",
        "investigating",
        "awaiting-analysis",
        "awaiting-decision",
    ):
        workflow.transition(
            EntityType.QUESTION,
            question.entity_id,
            state,
            actor_id="human:owner",
            actor_kind=ActorKind.HUMAN,
        )

    with pytest.raises(WorkflowGuardError, match="Question settlement requires"):
        workflow.transition(
            EntityType.QUESTION,
            question.entity_id,
            "settled",
            actor_id="human:owner",
            actor_kind=ActorKind.HUMAN,
        )
