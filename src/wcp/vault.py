"""Single-writer projection from WCP aggregates into an Obsidian vault."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

from wcp.events import EntityType
from wcp.store import EventStore


class VaultProjectionError(ValueError):
    pass


class VaultProjector:
    """Write deterministic machine-owned Markdown notes only under Machine/."""

    def __init__(self, vault_path: Path) -> None:
        self.vault_path = vault_path.expanduser().resolve()
        self.machine_root = self.vault_path / "Machine"

    def sync(self, store: EventStore, project_id: str) -> list[Path]:
        written: list[Path] = []
        for entity_type in EntityType:
            for aggregate in store.list(entity_type.value, project_id):
                destination = self._destination(aggregate)
                self._atomic_write(destination, self._render(aggregate))
                written.append(destination)
        self._write_review_queue(store, project_id)
        written.append(self.machine_root / "Dashboards/Review Queue.md")
        return written

    def _destination(self, aggregate: dict[str, Any]) -> Path:
        entity_type = EntityType(aggregate["entity_type"])
        data = aggregate["data"]
        name = str(data.get("key") or aggregate["id"])
        safe_name = "".join(
            character if character.isalnum() or character in "-_" else "-"
            for character in name
        ).strip("-")
        directories = {
            EntityType.QUESTION: "Domains/Research/Questions",
            EntityType.EXPERIMENT: "Domains/Research/Experiments",
            EntityType.CLAIM: "Domains/Research/Claims",
            EntityType.SESSION: "Sessions",
            EntityType.REVIEW: "Reviews",
        }
        return self.machine_root / directories[entity_type] / f"{safe_name}.md"

    def _render(self, aggregate: dict[str, Any]) -> str:
        data = aggregate["data"]
        title = str(data.get("title") or data.get("key") or aggregate["id"])
        frontmatter = {
            "schema_version": 1,
            "id": aggregate["id"],
            "type": aggregate["entity_type"],
            "project_id": aggregate["project_id"],
            "state": aggregate["state"],
            "version": aggregate["version"],
            "updated_at": aggregate["updated_at"],
        }
        metadata = yaml.safe_dump(frontmatter, sort_keys=False).strip()
        sections = [f"---\n{metadata}\n---", f"# {title}"]
        for key, value in data.items():
            if key in {"title", "key"}:
                continue
            heading = key.replace("_", " ").title()
            if isinstance(value, list):
                body = "\n".join(f"- {item}" for item in value) or "_None recorded._"
            elif isinstance(value, dict):
                body = (
                    "```yaml\n"
                    + yaml.safe_dump(value, sort_keys=False).strip()
                    + "\n```"
                )
            else:
                body = str(value)
            sections.append(f"## {heading}\n\n{body}")
        return "\n\n".join(sections) + "\n"

    def _write_review_queue(self, store: EventStore, project_id: str) -> None:
        reviews = [
            review
            for review in store.list(EntityType.REVIEW.value, project_id)
            if review["state"] in {"pending", "deferred"}
        ]
        lines = ["# Review Queue", ""]
        if reviews:
            for review in reviews:
                title = review["data"].get("title", review["id"])
                lines.append(
                    f"- [[../Reviews/{review['id']}|{title}]] — {review['state']}"
                )
        else:
            lines.append("_No pending reviews._")
        self._atomic_write(
            self.machine_root / "Dashboards/Review Queue.md", "\n".join(lines) + "\n"
        )

    def _atomic_write(self, path: Path, content: str) -> None:
        resolved = path.resolve()
        if self.machine_root not in resolved.parents:
            raise VaultProjectionError("Vault projector may write only under Machine/")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=resolved.parent, prefix=f".{resolved.name}.", suffix=".tmp", text=True
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(resolved)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
