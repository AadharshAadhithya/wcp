"""Small, replaceable adapter for reading Git repository identity."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from wcp.errors import GitError


@dataclass(frozen=True, slots=True)
class GitRepository:
    """Git facts needed during project initialization."""

    root: Path
    canonical_remote: str


def _git(path: Path, *arguments: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(path), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        detail = process.stderr.strip() or process.stdout.strip() or "unknown error"
        raise GitError(f"Git inspection failed: {detail}")
    return process.stdout.strip()


def inspect_repository(
    path: Path,
    remote_name: str = "origin",
    fallback_remote: str | None = None,
) -> GitRepository:
    """Resolve the repository root and its canonical remote URL."""

    candidate = path.expanduser().resolve()
    root_text = _git(candidate, "rev-parse", "--show-toplevel")
    root = Path(root_text).resolve()
    try:
        remote = _git(root, "remote", "get-url", remote_name)
    except GitError as error:
        if fallback_remote is None:
            raise GitError(
                f"Repository has no {remote_name!r} remote; pass --remote explicitly"
            ) from error
        remote = fallback_remote
    return GitRepository(root=root, canonical_remote=remote)
