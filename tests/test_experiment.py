from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from wcp.events import ActorKind, EntityType
from wcp.experiment import ExperimentDesign, LocalExperimentRunner
from wcp.store import EventStore
from wcp.workflow import Workflow

PROJECT_ID = "00000000000000000000000000"


def _repository(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True
    )
    (path / "README.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-qm", "initial"], check=True)


def _design(question_id: str) -> ExperimentDesign:
    return ExperimentDesign(
        key="NR-EXP-001",
        title="Smoke experiment",
        question_id=question_id,
        hypothesis="The command succeeds",
        rationale="Verify the vertical slice",
        decision="Whether to continue",
        competing_explanations=["The harness is broken"],
        predictions={"support": "exit 0", "refute": "non-zero exit"},
        controls=["fixed Python interpreter"],
        metrics=["return_code"],
        analysis_plan="Inspect exit status and logs",
        compute_budget="one local process",
        stopping_rule="one run",
    )


def test_clean_local_run_captures_provenance_and_artifacts(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    _repository(repository)
    workflow = Workflow(EventStore(tmp_path / "state.db"), PROJECT_ID)
    question = workflow.create(
        EntityType.QUESTION,
        {"key": "NR-RQ-001", "title": "Can the slice run?"},
        actor_id="human:owner",
        actor_kind=ActorKind.HUMAN,
    )
    experiment = workflow.create(
        EntityType.EXPERIMENT,
        _design(question.entity_id).model_dump(),
        actor_id="human:owner",
        actor_kind=ActorKind.HUMAN,
    )
    workflow.transition(
        EntityType.EXPERIMENT,
        experiment.entity_id,
        "ready",
        actor_id="human:owner",
        actor_kind=ActorKind.HUMAN,
    )

    result = LocalExperimentRunner(workflow, tmp_path / "artifacts").execute(
        experiment.entity_id,
        [sys.executable, "-c", "print('experiment output')"],
        repository=repository,
    )

    run = workflow.store.get("run", result.run_id)
    assert result.return_code == 0
    assert run["state"] == "succeeded"
    assert run["data"]["git"]["dirty"] is False
    assert result.manifest_path.exists()
    assert (
        result.run_directory / "stdout.log"
    ).read_text().strip() == "experiment output"
    assert (
        workflow.store.get("experiment", experiment.entity_id)["state"]
        == "awaiting-analysis"
    )
