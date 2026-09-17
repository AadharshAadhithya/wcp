"""Machine-local runtime path resolution."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def state_root() -> Path:
    """Return the user-level WCP state directory without creating it."""

    explicit = os.environ.get("WCP_STATE_DIR")
    if explicit:
        return Path(explicit).expanduser().resolve()
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        return Path(xdg).expanduser().resolve() / "wcp"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/WCP"
    return Path.home() / ".local/state/wcp"


def database_path(project_id: str, override: Path | None = None) -> Path:
    if override is not None:
        return override.expanduser().resolve()
    return state_root() / "projects" / project_id / "state.db"
