from pathlib import Path

from wcp.events import ActorKind, EntityType
from wcp.store import EventStore
from wcp.vault import VaultProjector
from wcp.workflow import Workflow

PROJECT_ID = "00000000000000000000000000"


def test_vault_projection_writes_machine_notes_and_preserves_human(
    tmp_path: Path,
) -> None:
    vault = tmp_path / "vault"
    human_note = vault / "Human/Home.md"
    human_note.parent.mkdir(parents=True)
    human_note.write_text("Human-owned\n", encoding="utf-8")
    store = EventStore(tmp_path / "state.db")
    workflow = Workflow(store, PROJECT_ID)
    question = workflow.create(
        EntityType.QUESTION,
        {
            "key": "NR-RQ-001",
            "title": "Does the receiver generalize?",
            "answer_criteria": ["Compare BLER against baseline"],
        },
        actor_id="human:owner",
        actor_kind=ActorKind.HUMAN,
    )

    written = VaultProjector(vault).sync(store, PROJECT_ID)

    question_note = vault / "Machine/Domains/Research/Questions/NR-RQ-001.md"
    assert question_note in written
    assert question.entity_id in question_note.read_text(encoding="utf-8")
    assert "Compare BLER" in question_note.read_text(encoding="utf-8")
    assert human_note.read_text(encoding="utf-8") == "Human-owned\n"
    assert (vault / "Machine/Dashboards/Review Queue.md").exists()
