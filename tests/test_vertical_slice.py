from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from wcp.events import ActorKind, EntityType
from wcp.experiment import LocalExperimentRunner
from wcp.sample import start_neural_receiver_sample
from wcp.store import EventStore
from wcp.vault import VaultProjector
from wcp.workflow import Workflow

PROJECT_ID = "00000000000000000000000000"


def _clean_repository(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True
    )
    (path / "README.md").write_text("vertical slice\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-qm", "initial"], check=True)


def test_local_vertical_slice_reaches_human_approved_settlement(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "state.db")
    workflow = Workflow(store, PROJECT_ID)
    sample = start_neural_receiver_sample(workflow)
    repository = tmp_path / "research"
    repository.mkdir()
    _clean_repository(repository)

    run = LocalExperimentRunner(workflow, tmp_path / "artifacts").execute(
        sample["experiment_id"],
        [sys.executable, "-c", "print('bler=0.10')"],
        repository=repository,
    )
    workflow.transition(
        EntityType.EXPERIMENT,
        sample["experiment_id"],
        "analyzed",
        actor_id="agent:codex",
        actor_kind=ActorKind.AGENT,
        data={"analysis": "Synthetic acceptance-test analysis only."},
    )
    for state in ("investigating", "awaiting-analysis", "awaiting-decision"):
        workflow.transition(
            EntityType.QUESTION,
            sample["question_id"],
            state,
            actor_id="agent:codex",
            actor_kind=ActorKind.AGENT,
        )

    claim = workflow.create(
        EntityType.CLAIM,
        {
            "question_id": sample["question_id"],
            "title": "The test run completed",
            "exact_scope": "WCP acceptance-test command only",
            "supporting_evidence": [run.run_id],
            "confidence": "high",
            "limitations": [
                "This is infrastructure validation, not scientific evidence."
            ],
        },
        actor_id="agent:codex",
        actor_kind=ActorKind.AGENT,
    )
    workflow.transition(
        EntityType.CLAIM,
        claim.entity_id,
        "pending-review",
        actor_id="agent:codex",
        actor_kind=ActorKind.AGENT,
    )
    workflow.transition(
        EntityType.CLAIM,
        claim.entity_id,
        "accepted",
        actor_id="human:owner",
        actor_kind=ActorKind.HUMAN,
    )
    workflow.transition(
        EntityType.QUESTION,
        sample["question_id"],
        "settled",
        actor_id="human:owner",
        actor_kind=ActorKind.HUMAN,
        data={
            "evidence_ids": [run.run_id],
            "claim_ids": [claim.entity_id],
            "limitations": ["Infrastructure-only synthetic run."],
            "confidence": "high for workflow behavior only",
            "follow_up_questions": ["What does the real neural experiment show?"],
            "conclusion": "The local WCP vertical-slice mechanics operate end to end.",
        },
    )

    VaultProjector(tmp_path / "vault").sync(store, PROJECT_ID)

    assert store.get("question", sample["question_id"])["state"] == "settled"
    assert store.get("claim", claim.entity_id)["data"]["approved_by"] == "human:owner"
    assert (tmp_path / "vault/Machine/Domains/Research/Claims").is_dir()
