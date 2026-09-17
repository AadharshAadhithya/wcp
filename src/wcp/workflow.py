"""Application service for recording semantic workflow operations."""

from __future__ import annotations

from typing import Any

from wcp.errors import WcpError
from wcp.events import ActorKind, EntityType, Event, StoredEvent
from wcp.ids import new_ulid
from wcp.store import EventStore


class WorkflowGuardError(WcpError):
    """Raised when a human-judgment or evidence invariant is not satisfied."""


class Workflow:
    def __init__(self, store: EventStore, project_id: str) -> None:
        self.store = store
        self.project_id = project_id

    def create(
        self,
        entity_type: EntityType,
        data: dict[str, Any],
        *,
        actor_id: str,
        actor_kind: ActorKind,
        entity_id: str | None = None,
        session_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> StoredEvent:
        entity_id = entity_id or new_ulid()
        return self.store.append(
            Event(
                project_id=self.project_id,
                entity_type=entity_type,
                entity_id=entity_id,
                event_type=f"{entity_type.value}.created",
                actor_id=actor_id,
                actor_kind=actor_kind,
                session_id=session_id,
                payload=data,
                idempotency_key=idempotency_key or f"{entity_id}:created",
            )
        )

    def transition(
        self,
        entity_type: EntityType,
        entity_id: str,
        target: str,
        *,
        actor_id: str,
        actor_kind: ActorKind,
        data: dict[str, Any] | None = None,
        session_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> StoredEvent:
        if (
            entity_type is EntityType.CLAIM
            and target in {"accepted", "rejected"}
            and actor_kind is not ActorKind.HUMAN
        ):
            raise ValueError("Only a human actor may accept or reject a claim")
        if (
            entity_type is EntityType.QUESTION
            and target == "settled"
            and actor_kind is not ActorKind.HUMAN
        ):
            raise ValueError("Only a human actor may settle a research question")
        if (
            entity_type is EntityType.REVIEW
            and target in {"accepted", "rejected"}
            and actor_kind is not ActorKind.HUMAN
        ):
            raise ValueError("Only a human actor may accept or reject a review")

        transition_data = dict(data or {})
        if entity_type is EntityType.CLAIM and target == "accepted":
            self._validate_claim_acceptance(entity_id, transition_data)
            transition_data["approved_by"] = actor_id
        if entity_type is EntityType.QUESTION and target == "settled":
            self._validate_question_settlement(entity_id, transition_data)
            transition_data["approved_by"] = actor_id
        return self.store.append(
            Event(
                project_id=self.project_id,
                entity_type=entity_type,
                entity_id=entity_id,
                event_type=f"{entity_type.value}.transitioned",
                actor_id=actor_id,
                actor_kind=actor_kind,
                session_id=session_id,
                payload={"to": target, "data": transition_data},
                idempotency_key=idempotency_key or new_ulid(),
            )
        )

    def _validate_claim_acceptance(
        self, entity_id: str, transition_data: dict[str, Any]
    ) -> None:
        claim = self.store.get(EntityType.CLAIM.value, entity_id)
        if claim is None:
            raise WorkflowGuardError(f"No claim {entity_id}")
        combined = {**claim["data"], **transition_data}
        required = ("exact_scope", "supporting_evidence", "confidence", "limitations")
        missing = [field for field in required if not combined.get(field)]
        if missing:
            raise WorkflowGuardError("Claim acceptance requires: " + ", ".join(missing))

    def _validate_question_settlement(
        self, entity_id: str, transition_data: dict[str, Any]
    ) -> None:
        question = self.store.get(EntityType.QUESTION.value, entity_id)
        if question is None:
            raise WorkflowGuardError(f"No question {entity_id}")
        combined = {**question["data"], **transition_data}
        required = (
            "scope",
            "answer_criteria",
            "evidence_ids",
            "claim_ids",
            "competing_explanations",
            "limitations",
            "confidence",
            "follow_up_questions",
            "conclusion",
        )
        missing = [field for field in required if not combined.get(field)]
        if missing:
            raise WorkflowGuardError(
                "Question settlement requires: " + ", ".join(missing)
            )
        for claim_id in combined["claim_ids"]:
            claim = self.store.get(EntityType.CLAIM.value, claim_id)
            if claim is None or claim["state"] != "accepted":
                raise WorkflowGuardError(
                    f"Question settlement requires accepted claim {claim_id}"
                )

    def record(
        self,
        entity_type: EntityType,
        entity_id: str,
        data: dict[str, Any],
        *,
        actor_id: str,
        actor_kind: ActorKind,
        session_id: str | None = None,
        evidence: tuple[str, ...] = (),
        idempotency_key: str | None = None,
    ) -> StoredEvent:
        return self.store.append(
            Event(
                project_id=self.project_id,
                entity_type=entity_type,
                entity_id=entity_id,
                event_type=f"{entity_type.value}.recorded",
                actor_id=actor_id,
                actor_kind=actor_kind,
                session_id=session_id,
                evidence=evidence,
                payload=data,
                idempotency_key=idempotency_key or new_ulid(),
            )
        )
