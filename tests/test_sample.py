from pathlib import Path

from wcp.sample import start_neural_receiver_sample
from wcp.store import EventStore
from wcp.workflow import Workflow

PROJECT_ID = "00000000000000000000000000"


def test_neural_receiver_sample_is_complete_and_idempotent(tmp_path: Path) -> None:
    workflow = Workflow(EventStore(tmp_path / "state.db"), PROJECT_ID)

    first = start_neural_receiver_sample(workflow)
    second = start_neural_receiver_sample(workflow)

    assert first == second
    assert first["question_state"] == "ready"
    assert first["experiment_state"] == "ready"
    assert len(workflow.store.list("question", PROJECT_ID)) == 1
    assert len(workflow.store.list("experiment", PROJECT_ID)) == 1
