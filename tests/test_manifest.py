from pathlib import Path

import pytest

from wcp.errors import ManifestError
from wcp.manifest import Domain, ProjectManifest, dump_manifest, load_manifest


def test_manifest_round_trip() -> None:
    manifest = ProjectManifest.model_validate(
        {
            "schema_version": 1,
            "project": {
                "id": "00000000000000000000000000",
                "key": "nr",
                "title": "Neural Receiver",
                "domain": "research",
            },
            "git": {"canonical_remote": "git@github.com:owner/project.git"},
        }
    )

    assert manifest.project.key == "NR"
    assert manifest.project.domain is Domain.RESEARCH
    assert "tracker: mlflow" in dump_manifest(manifest)


def test_manifest_rejects_unknown_fields(tmp_path: Path) -> None:
    manifest = tmp_path / "project.yaml"
    manifest.write_text(
        "schema_version: 1\n"
        "project:\n"
        "  id: 00000000000000000000000000\n"
        "  key: NR\n"
        "  title: Neural Receiver\n"
        "  domain: research\n"
        "git:\n"
        "  canonical_remote: example\n"
        "surprise: true\n",
        encoding="utf-8",
    )

    with pytest.raises(ManifestError, match="extra_forbidden"):
        load_manifest(manifest)


def test_manifest_accepts_adapter_native_link_ids() -> None:
    manifest = ProjectManifest.model_validate(
        {
            "project": {
                "id": "00000000000000000000000000",
                "key": "NR",
                "title": "Neural Receiver",
                "domain": "research",
            },
            "git": {"canonical_remote": "example"},
            "links": {
                "vault_entity_id": "Machine/Domains/Research/Projects/NR.md",
                "plane_project_id": "e1c25c66-5bb8-465e-a818-92a483423443",
            },
        }
    )

    assert manifest.links.plane_project_id.startswith("e1c25c66")
