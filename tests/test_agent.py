from pathlib import Path

import pytest

from wcp.agent import AgentTools
from wcp.events import EntityType
from wcp.store import EventStore
from wcp.workflow import Workflow

PROJECT_ID = "00000000000000000000000000"


def test_agent_tools_write_semantic_events_but_cannot_approve(tmp_path: Path) -> None:
    tools = AgentTools(Workflow(EventStore(tmp_path / "state.db"), PROJECT_ID))
    claim = tools.create_entity(
        "claim",
        {
            "title": "Claim",
            "exact_scope": "Test scope",
            "supporting_evidence": ["run:1"],
            "confidence": "low",
            "limitations": ["pilot"],
        },
    )
    tools.transition_entity("claim", claim["id"], "pending-review")

    with pytest.raises(ValueError, match="Only a human"):
        tools.transition_entity("claim", claim["id"], "accepted")

    assert len(tools.list_entities(EntityType.CLAIM.value)) == 1
