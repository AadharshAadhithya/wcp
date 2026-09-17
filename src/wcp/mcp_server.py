"""Local stdio MCP server exposing capability-limited WCP operations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server import MCPServer

from wcp.agent import AgentTools

mcp = MCPServer("WCP")


def _tools() -> AgentTools:
    project_path = Path(os.environ.get("WCP_PROJECT_PATH", Path.cwd()))
    actor_id = os.environ.get("WCP_ACTOR_ID", "agent:codex")
    db_value = os.environ.get("WCP_DATABASE_PATH")
    return AgentTools.from_project(
        project_path,
        actor_id=actor_id,
        db_path=Path(db_value) if db_value else None,
    )


@mcp.tool()
def project_context() -> dict[str, Any]:
    """Return the active WCP project identity and this agent's capabilities."""

    return _tools().project_context()


@mcp.tool()
def create_entity(
    entity_type: str,
    data: dict[str, Any],
    session_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Create a question, session, experiment, run, claim, or review."""

    return _tools().create_entity(
        entity_type,
        data,
        session_id=session_id,
        idempotency_key=idempotency_key,
    )


@mcp.tool()
def transition_entity(
    entity_type: str,
    entity_id: str,
    target: str,
    data: dict[str, Any] | None = None,
    session_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Request a valid transition; human-only decisions are rejected."""

    return _tools().transition_entity(
        entity_type,
        entity_id,
        target,
        data=data,
        session_id=session_id,
        idempotency_key=idempotency_key,
    )


@mcp.tool()
def record_entity(
    entity_type: str,
    entity_id: str,
    data: dict[str, Any],
    evidence: list[str] | None = None,
    session_id: str | None = None,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Attach semantic data and evidence references to an existing entity."""

    return _tools().record_entity(
        entity_type,
        entity_id,
        data,
        evidence=evidence,
        session_id=session_id,
        idempotency_key=idempotency_key,
    )


@mcp.tool()
def get_entity(entity_type: str, entity_id: str) -> dict[str, Any]:
    """Read current projected state for one WCP entity."""

    return _tools().get_entity(entity_type, entity_id)


@mcp.tool()
def list_entities(entity_type: str) -> list[dict[str, Any]]:
    """List current projected entities of one type in the active project."""

    return _tools().list_entities(entity_type)


def main() -> None:
    mcp.run()


if __name__ == "__main__":  # pragma: no cover
    main()
