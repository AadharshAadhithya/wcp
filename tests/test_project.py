from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from wcp.errors import InitializationConflict
from wcp.git import GitRepository
from wcp.manifest import Domain, load_manifest
from wcp.project import initialize_project


@pytest.fixture
def repository(tmp_path: Path) -> GitRepository:
    return GitRepository(
        root=tmp_path.resolve(),
        canonical_remote="git@github.com:owner/example.git",
    )


def test_init_creates_manifest_and_is_idempotent(repository: GitRepository) -> None:
    with patch("wcp.project.inspect_repository", return_value=repository):
        first = initialize_project(
            repository.root,
            key="EX",
            title="Example",
            domain=Domain.DEV,
        )
        second = initialize_project(repository.root)

    assert first.created is True
    assert first.updated is False
    assert second.created is False
    assert second.updated is False
    assert second.manifest.project.id == first.manifest.project.id
    assert second.manifest.git.canonical_remote == repository.canonical_remote
    assert load_manifest(first.manifest_path) == first.manifest


def test_init_requires_identity_for_new_project(repository: GitRepository) -> None:
    with (
        patch("wcp.project.inspect_repository", return_value=repository),
        pytest.raises(InitializationConflict, match="--title, --domain"),
    ):
        initialize_project(repository.root, key="EX")


def test_init_refuses_to_change_existing_identity(repository: GitRepository) -> None:
    with patch("wcp.project.inspect_repository", return_value=repository):
        initialize_project(
            repository.root,
            key="EX",
            title="Example",
            domain=Domain.DEV,
        )
        with pytest.raises(InitializationConflict, match="project key"):
            initialize_project(repository.root, key="OTHER")


def test_init_adds_missing_link_but_refuses_to_replace_it(
    repository: GitRepository,
) -> None:
    first_link = "00000000000000000000000000"
    second_link = "00000000000000000000000001"
    with patch("wcp.project.inspect_repository", return_value=repository):
        initialize_project(
            repository.root,
            key="EX",
            title="Example",
            domain=Domain.DEV,
        )
        linked = initialize_project(repository.root, vault_entity_id=first_link)

        assert linked.updated is True
        assert linked.manifest.links.vault_entity_id == first_link

        with pytest.raises(InitializationConflict, match="vault_entity_id"):
            initialize_project(repository.root, vault_entity_id=second_link)
