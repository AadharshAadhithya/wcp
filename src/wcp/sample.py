"""Idempotent starter data for the v1 neural-receiver vertical slice."""

from __future__ import annotations

from typing import Any

from wcp.events import ActorKind, EntityType
from wcp.experiment import ExperimentDesign
from wcp.workflow import Workflow


def _by_key(
    workflow: Workflow, entity_type: EntityType, key: str
) -> dict[str, Any] | None:
    return next(
        (
            item
            for item in workflow.store.list(entity_type.value, workflow.project_id)
            if item["data"].get("key") == key
        ),
        None,
    )


def start_neural_receiver_sample(workflow: Workflow) -> dict[str, Any]:
    """Create the agreed sample question and its smallest informative experiment."""

    question = _by_key(workflow, EntityType.QUESTION, "NR-RQ-001")
    if question is None:
        created = workflow.create(
            EntityType.QUESTION,
            {
                "key": "NR-RQ-001",
                "title": "Generalization to unseen channel conditions",
                "question": (
                    "Does a neural receiver trained on one channel distribution "
                    "maintain a BLER advantage over a classical baseline on unseen "
                    "channel conditions?"
                ),
            },
            actor_id="human:owner",
            actor_kind=ActorKind.HUMAN,
            idempotency_key=f"{workflow.project_id}:sample:NR-RQ-001:create",
        )
        question_id = created.entity_id
        workflow.transition(
            EntityType.QUESTION,
            question_id,
            "framing",
            actor_id="human:owner",
            actor_kind=ActorKind.HUMAN,
            data={
                "scope": (
                    "One neural-receiver checkpoint evaluated on at least one held-out "
                    "channel family under a matched simulation budget."
                ),
                "answer_criteria": [
                    "Report BLER versus Eb/N0 for neural and classical receivers.",
                    "Include uncertainty across at least three deterministic seeds.",
                    "Record whether any advantage persists across the held-out range.",
                ],
                "competing_explanations": [
                    "Any apparent gain is caused by a mismatched or weaker baseline.",
                    (
                        "The gain is limited to channel conditions represented in "
                        "training."
                    ),
                    (
                        "The observed difference is seed variance rather than "
                        "generalization."
                    ),
                ],
            },
            idempotency_key=f"{workflow.project_id}:sample:NR-RQ-001:frame",
        )
        workflow.transition(
            EntityType.QUESTION,
            question_id,
            "ready",
            actor_id="human:owner",
            actor_kind=ActorKind.HUMAN,
            data={"primary": True},
            idempotency_key=f"{workflow.project_id}:sample:NR-RQ-001:ready",
        )
        question = workflow.store.get(EntityType.QUESTION.value, question_id)
    assert question is not None

    experiment = _by_key(workflow, EntityType.EXPERIMENT, "NR-EXP-001")
    if experiment is None:
        design = ExperimentDesign(
            key="NR-EXP-001",
            title="Held-out channel generalization pilot",
            question_id=question["id"],
            hypothesis=(
                "The neural receiver retains a measurable BLER advantage over the "
                "classical baseline on a held-out channel family."
            ),
            rationale=(
                "This is the smallest run that can challenge in-distribution gains."
            ),
            decision=(
                "Whether to invest in a larger multi-channel, multi-seed "
                "generalization study."
            ),
            competing_explanations=question["data"]["competing_explanations"],
            predictions={
                "support": (
                    "Neural BLER is lower across a preregistered Eb/N0 interval."
                ),
                "refute": "The classical baseline matches or beats neural BLER.",
                "inconclusive": "Intervals overlap or protocol checks fail.",
            },
            controls=[
                "Identical waveform, dataset, and channel samples for both receivers.",
                "Matched evaluation seeds and Eb/N0 grid.",
                "No checkpoint selection using held-out results.",
            ],
            metrics=["bler", "ber", "runtime_seconds"],
            analysis_plan=(
                "Plot BLER and BER by Eb/N0, aggregate across seeds, compare "
                "confidence intervals, and inspect protocol deviations before "
                "inference."
            ),
            compute_budget=(
                "Pilot only: three seeds and the smallest informative Eb/N0 grid."
            ),
            stopping_rule=(
                "Stop after all preregistered seeds finish or after one "
                "protocol-invalid run."
            ),
        )
        created = workflow.create(
            EntityType.EXPERIMENT,
            design.model_dump(mode="json"),
            actor_id="human:owner",
            actor_kind=ActorKind.HUMAN,
            idempotency_key=f"{workflow.project_id}:sample:NR-EXP-001:create",
        )
        workflow.transition(
            EntityType.EXPERIMENT,
            created.entity_id,
            "ready",
            actor_id="human:owner",
            actor_kind=ActorKind.HUMAN,
            idempotency_key=f"{workflow.project_id}:sample:NR-EXP-001:ready",
        )
        experiment = workflow.store.get(EntityType.EXPERIMENT.value, created.entity_id)
    assert experiment is not None
    return {
        "question_id": question["id"],
        "question_state": question["state"],
        "experiment_id": experiment["id"],
        "experiment_state": experiment["state"],
        "next": (
            "wcp experiment execute "
            f"{experiment['id']} -- <your neural-receiver evaluation command>"
        ),
    }
