from __future__ import annotations

import gzip
import json
from pathlib import Path

from wcp.archive import SessionArchive


def test_archive_spools_and_seals_immutable_transcript(tmp_path: Path) -> None:
    archive = SessionArchive(tmp_path / "archive")
    archive.append("session", '{"type":"turn.started"}')
    destination, checksum = archive.seal("session")

    with gzip.open(destination, "rt", encoding="utf-8") as stream:
        assert stream.read() == '{"type":"turn.started"}\n'
    metadata = json.loads(
        (tmp_path / "archive/sealed/session.sha256.json").read_text(encoding="utf-8")
    )
    assert metadata["checksum"] == checksum
    assert not (tmp_path / "archive/spool/session.jsonl").exists()
