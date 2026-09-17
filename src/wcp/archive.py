"""Crash-safe local spool and immutable compressed Session Archive."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path


class SessionArchive:
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()
        self.spool = self.root / "spool"
        self.sealed = self.root / "sealed"

    def append(self, session_id: str, raw_line: str) -> None:
        self.spool.mkdir(parents=True, exist_ok=True)
        line = raw_line.rstrip("\n") + "\n"
        with (self.spool / f"{session_id}.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(line)
            stream.flush()
            os.fsync(stream.fileno())

    def seal(self, session_id: str) -> tuple[Path, str]:
        source = self.spool / f"{session_id}.jsonl"
        if not source.exists():
            raise ValueError(f"No transcript spool exists for session {session_id}")
        self.sealed.mkdir(parents=True, exist_ok=True)
        destination = self.sealed / f"{session_id}.jsonl.gz"
        checksum_path = self.sealed / f"{session_id}.sha256.json"
        if destination.exists() or checksum_path.exists():
            raise ValueError(f"Session {session_id} is already sealed")

        digest = hashlib.sha256()
        with (
            source.open("rb") as input_stream,
            destination.open("xb") as raw_output,
            gzip.GzipFile(fileobj=raw_output, mode="wb", mtime=0) as output,
        ):
            while chunk := input_stream.read(1024 * 1024):
                digest.update(chunk)
                output.write(chunk)
        checksum = digest.hexdigest()
        checksum_path.write_text(
            json.dumps(
                {
                    "algorithm": "sha256",
                    "checksum": checksum,
                    "session_id": session_id,
                    "archive": destination.name,
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        source.unlink()
        return destination, checksum
