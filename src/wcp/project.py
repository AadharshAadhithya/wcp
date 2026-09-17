"""Project initialization use case."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from wcp.errors import InitializationConflict
from wcp.git import inspect_repository
from wcp.ids import new_ulid
from wcp.manifest import (
    Domain,
    GitIdentity,
    ProjectIdentity,
    ProjectLinks,
    ProjectManifest,
    dump_manifest,
    load_manifest,
)

MANIFEST_RELATIVE_PATH = Path(".wcp/project.yaml")


@dataclass(frozen=True, slots=True)
class InitializationResult:
    manifest_path: Path
    manifest: ProjectManifest
    created: bool
    updated: bool = False


def _assert_matches(
    manifest: ProjectManifest,
    *,
    key: str | None,
    title: str | None,
    domain: Domain | None,
    remote: str | None,
) -> None:
    expected = {
        "project key": (manifest.project.key, key.strip().upper() if key else None),
        "project title": (manifest.project.title, title.strip() if title else None),
        "project domain": (manifest.project.domain, domain),
        "canonical remote": (manifest.git.canonical_remote, remote),
    }
    conflicts = [
        f"{label} is {actual!r}, not {requested!r}"
        for label, (actual, requested) in expected.items()
        if requested is not None and actual != requested
    ]
    if conflicts:
        raise InitializationConflict(
            "Existing project identity conflicts with init arguments: "
            + "; ".join(conflicts)
        )


def _merge_links(
    manifest: ProjectManifest,
    *,
    vault_entity_id: str | None,
    plane_workspace_id: str | None,
    plane_project_id: str | None,
) -> ProjectManifest:
    requested = {
        "vault_entity_id": vault_entity_id,
        "plane_workspace_id": plane_workspace_id,
        "plane_project_id": plane_project_id,
    }
    updates: dict[str, str] = {}
    conflicts: list[str] = []
    for field, value in requested.items():
        if value is None:
            continue
        existing = getattr(manifest.links, field)
        if existing is None:
            updates[field] = value
        elif existing != value:
            conflicts.append(f"{field} is {existing!r}, not {value!r}")

    if conflicts:
        raise InitializationConflict(
            "Existing project links conflict with init arguments: "
            + "; ".join(conflicts)
        )
    if not updates:
        return manifest
    links = ProjectLinks.model_validate({**manifest.links.model_dump(), **updates})
    return manifest.model_copy(update={"links": links})


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.replace(path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def initialize_project(
    path: Path,
    *,
    key: str | None = None,
    title: str | None = None,
    domain: Domain | None = None,
    remote: str | None = None,
    vault_entity_id: str | None = None,
    plane_workspace_id: str | None = None,
    plane_project_id: str | None = None,
) -> InitializationResult:
    """Create a project identity, or safely return the existing identity."""

    repository = inspect_repository(path, fallback_remote=remote)
    manifest_path = repository.root / MANIFEST_RELATIVE_PATH
    resolved_remote = remote or repository.canonical_remote

    if manifest_path.exists():
        manifest = load_manifest(manifest_path)
        _assert_matches(
            manifest,
            key=key,
            title=title,
            domain=domain,
            remote=remote,
        )
        updated_manifest = _merge_links(
            manifest,
            vault_entity_id=vault_entity_id,
            plane_workspace_id=plane_workspace_id,
            plane_project_id=plane_project_id,
        )
        updated = updated_manifest != manifest
        if updated:
            _atomic_write(manifest_path, dump_manifest(updated_manifest))
        return InitializationResult(
            manifest_path, updated_manifest, created=False, updated=updated
        )

    missing = [
        flag
        for flag, value in (("--key", key), ("--title", title), ("--domain", domain))
        if value is None
    ]
    if missing:
        raise InitializationConflict("New projects require " + ", ".join(missing) + ".")

    manifest = ProjectManifest(
        project=ProjectIdentity(
            id=new_ulid(),
            key=key,
            title=title,
            domain=domain,
        ),
        git=GitIdentity(canonical_remote=resolved_remote),
        links=ProjectLinks(
            vault_entity_id=vault_entity_id,
            plane_workspace_id=plane_workspace_id,
            plane_project_id=plane_project_id,
        ),
    )
    _atomic_write(manifest_path, dump_manifest(manifest))
    return InitializationResult(manifest_path, manifest, created=True)
