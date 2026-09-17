from pathlib import Path
from unittest.mock import patch

from wcp.errors import GitError
from wcp.git import inspect_repository


def test_explicit_remote_allows_repository_without_origin(tmp_path: Path) -> None:
    def git_response(_path: Path, *arguments: str) -> str:
        if arguments[0] == "rev-parse":
            return str(tmp_path)
        raise GitError("missing remote")

    with patch("wcp.git._git", side_effect=git_response):
        repository = inspect_repository(tmp_path, fallback_remote="ssh://example/repo")

    assert repository.root == tmp_path.resolve()
    assert repository.canonical_remote == "ssh://example/repo"
