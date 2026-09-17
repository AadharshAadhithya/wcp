from __future__ import annotations

import asyncio
from pathlib import Path

from mcp import Client

from wcp.mcp_server import mcp


def test_mcp_server_exposes_project_context(
    tmp_path: Path, monkeypatch: object
) -> None:
    monkeypatch.setenv("WCP_PROJECT_PATH", str(Path.cwd()))
    monkeypatch.setenv("WCP_DATABASE_PATH", str(tmp_path / "state.db"))

    async def call() -> dict[str, object]:
        async with Client(mcp) as client:
            result = await client.call_tool("project_context", {})
            assert result.structured_content is not None
            return result.structured_content

    context = asyncio.run(call())
    assert context["project_id"] == "01M2RND4KKR97VSZGQ74GYADHR"
    assert "settle research questions" in context["human_only"]
