"""Versioned project manifest schema and serialization."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
)

from wcp.errors import ManifestError
from wcp.ids import is_ulid

ProjectKey = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[A-Z][A-Z0-9-]{1,15}$"),
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Domain(StrEnum):
    RESEARCH = "research"
    HEALTH = "health"
    DEV = "dev"
    PERSONAL = "personal"
    LEARNING = "learning"
    FINANCE_AND_ADMIN = "finance-and-admin"


class ProjectIdentity(StrictModel):
    id: str
    key: ProjectKey
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    domain: Domain

    @field_validator("key", mode="before")
    @classmethod
    def normalize_key(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if not is_ulid(value):
            raise ValueError("project id must be a canonical ULID")
        return value


class GitIdentity(StrictModel):
    canonical_remote: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1)
    ]


class ProjectLinks(StrictModel):
    vault_entity_id: str | None = None
    plane_workspace_id: str | None = None
    plane_project_id: str | None = None


class ProjectDefaults(StrictModel):
    tracker: str = "mlflow"
    artifact_profile: str = "vpn-storage"
    policy_profile: str = "research-default"


class ProjectManifest(StrictModel):
    schema_version: Literal[1] = 1
    project: ProjectIdentity
    git: GitIdentity
    links: ProjectLinks = Field(default_factory=ProjectLinks)
    defaults: ProjectDefaults = Field(default_factory=ProjectDefaults)


def load_manifest(path: Path) -> ProjectManifest:
    """Load and strictly validate a project manifest."""

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ManifestError(f"Could not read {path}: {error}") from error
    except yaml.YAMLError as error:
        raise ManifestError(f"Invalid YAML in {path}: {error}") from error

    if not isinstance(raw, dict):
        raise ManifestError(f"Manifest {path} must contain a YAML mapping")
    try:
        return ProjectManifest.model_validate(raw)
    except (ValidationError, ValueError) as error:
        raise ManifestError(f"Invalid project manifest {path}: {error}") from error


def dump_manifest(manifest: ProjectManifest) -> str:
    """Serialize a manifest deterministically for stable Git diffs."""

    data = manifest.model_dump(mode="json")
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
