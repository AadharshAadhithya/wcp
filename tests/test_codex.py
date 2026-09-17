from pathlib import Path

from wcp.archive import SessionArchive
from wcp.codex import CodexStreamIngestor
from wcp.store import EventStore
from wcp.workflow import Workflow

PROJECT_ID = "00000000000000000000000000"


def test_codex_jsonl_becomes_session_events_and_archive(tmp_path: Path) -> None:
    store = EventStore(tmp_path / "state.db")
    ingestor = CodexStreamIngestor(
        Workflow(store, PROJECT_ID), SessionArchive(tmp_path / "archive")
    )

    result = ingestor.ingest(
        [
            '{"type":"thread.started","thread_id":"thread-1"}\n',
            '{"type":"item.completed","item":{"type":"agent_message","text":"Done"}}\n',
        ],
        mode="delegated",
    )

    session = store.get("session", result.session_id)
    assert result.event_count == 2
    assert result.archive_path.exists()
    assert session["state"] == "completed"
    assert session["data"]["archive_sha256"] == result.checksum
    assert session["data"]["last_codex_event"]["type"] == "item.completed"
