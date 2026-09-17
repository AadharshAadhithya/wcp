"""Reproducible local experiment execution and run provenance."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from wcp.events import ActorKind, EntityType
from wcp.ids import new_ulid
from wcp.workflow import Workflow


class ExperimentDesign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2)]
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    question_id: str
    hypothesis: str
    rationale: str
    decision: str
    competing_explanations: list[str] = Field(min_length=1)
    predictions: dict[str, str]
    controls: list[str] = Field(min_length=1)
    metrics: list[str] = Field(min_length=1)
    analysis_plan: str
    compute_budget: str
    stopping_rule: str
    config_paths: list[str] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RunResult:
    experiment_id: str
    run_id: str
    return_code: int
    run_directory: Path
    manifest_path: Path


def _command(repository: Path, *arguments: str, binary: bool = False) -> str | bytes:
    process = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=False,
        capture_output=True,
        text=not binary,
    )
    if process.returncode != 0:
        stderr = process.stderr
        detail = stderr.decode(errors="replace") if binary else stderr
        raise ValueError(f"Git provenance failed: {str(detail).strip()}")
    return process.stdout


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _git_provenance(repository: Path, run_directory: Path) -> dict[str, Any]:
    commit = str(_command(repository, "rev-parse", "HEAD")).strip()
    status = str(_command(repository, "status", "--porcelain=v1", "-z"))
    dirty = bool(status)
    provenance: dict[str, Any] = {"commit": commit, "dirty": dirty}
    if not dirty:
        return provenance

    diff = _command(repository, "diff", "HEAD", "--binary", binary=True)
    assert isinstance(diff, bytes)
    diff_path = run_directory / "dirty-tree.patch"
    diff_path.write_bytes(diff)
    raw_paths = status.split("\0")
    untracked: list[dict[str, Any]] = []
    for entry in raw_paths:
        if not entry.startswith("?? "):
            continue
        relative = entry[3:]
        candidate = repository / relative
        if candidate.is_file():
            untracked.append(
                {
                    "path": relative,
                    "size": candidate.stat().st_size,
                    "sha256": _sha256(candidate),
                }
            )
    untracked_path = run_directory / "untracked-files.json"
    untracked_path.write_text(
        json.dumps(untracked, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    tree_digest = hashlib.sha256()
    tree_digest.update(status.encode())
    tree_digest.update(diff)
    tree_digest.update(untracked_path.read_bytes())
    provenance.update(
        {
            "diff": str(diff_path),
            "diff_sha256": _sha256(diff_path),
            "untracked_manifest": str(untracked_path),
            "tree_digest": tree_digest.hexdigest(),
        }
    )
    return provenance


def _dependency_state(repository: Path) -> list[dict[str, Any]]:
    names = (
        "uv.lock",
        "poetry.lock",
        "requirements.txt",
        "package-lock.json",
        "Cargo.lock",
    )
    return [
        {"path": name, "sha256": _sha256(repository / name)}
        for name in names
        if (repository / name).is_file()
    ]


class LocalExperimentRunner:
    def __init__(self, workflow: Workflow, artifact_root: Path) -> None:
        self.workflow = workflow
        self.artifact_root = artifact_root.expanduser().resolve()

    def execute(
        self,
        experiment_id: str,
        command: list[str],
        *,
        repository: Path,
        actor_id: str = "human:owner",
        exploratory: bool = False,
        metrics_file: Path | None = None,
    ) -> RunResult:
        if not command:
            raise ValueError("Experiment command must not be empty")
        experiment = self.workflow.store.get(EntityType.EXPERIMENT.value, experiment_id)
        if experiment is None:
            raise ValueError(f"No experiment {experiment_id}")
        if experiment["state"] != "ready":
            raise ValueError("Experiment must be ready before launch")

        repository = repository.expanduser().resolve()
        run_id = new_ulid()
        run_directory = self.artifact_root / "runs" / run_id
        run_directory.mkdir(parents=True, exist_ok=False)
        provenance = _git_provenance(repository, run_directory)
        if provenance["dirty"] and not exploratory:
            shutil.rmtree(run_directory)
            raise ValueError(
                "Normal runs require a clean Git checkout; use --exploratory "
                "to capture a dirty tree"
            )

        configs: list[dict[str, Any]] = []
        for raw_path in experiment["data"].get("config_paths", []):
            source = (repository / raw_path).resolve()
            if repository not in source.parents or not source.is_file():
                raise ValueError(
                    f"Config path is missing or outside the repository: {raw_path}"
                )
            destination = run_directory / "configs" / raw_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            configs.append({"path": raw_path, "sha256": _sha256(destination)})

        run = self.workflow.create(
            EntityType.RUN,
            {
                "experiment_id": experiment_id,
                "question_id": experiment["data"].get("question_id"),
                "command": command,
                "exploratory": exploratory,
            },
            actor_id=actor_id,
            actor_kind=ActorKind.HUMAN,
            entity_id=run_id,
        )
        self.workflow.transition(
            EntityType.EXPERIMENT,
            experiment_id,
            "active",
            actor_id=actor_id,
            actor_kind=ActorKind.HUMAN,
        )
        launch_data = {
            "git": provenance,
            "configs": configs,
            "dependency_state": _dependency_state(repository),
            "artifact_directory": str(run_directory),
        }
        self.workflow.transition(
            EntityType.RUN,
            run.entity_id,
            "launched",
            actor_id=actor_id,
            actor_kind=ActorKind.HUMAN,
            data=launch_data,
        )
        self.workflow.transition(
            EntityType.RUN,
            run.entity_id,
            "running",
            actor_id=actor_id,
            actor_kind=ActorKind.HUMAN,
        )

        stdout_path = run_directory / "stdout.log"
        stderr_path = run_directory / "stderr.log"
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process = subprocess.run(
                command,
                cwd=repository,
                check=False,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
            )

        artifacts: list[dict[str, Any]] = [
            {"path": str(path), "size": path.stat().st_size, "sha256": _sha256(path)}
            for path in (stdout_path, stderr_path)
        ]
        metrics: dict[str, Any] = {}
        if metrics_file is not None:
            source = (
                metrics_file
                if metrics_file.is_absolute()
                else repository / metrics_file
            )
            if source.exists():
                metrics = json.loads(source.read_text(encoding="utf-8"))
                copied_metrics = run_directory / "metrics.json"
                shutil.copyfile(source, copied_metrics)
                artifacts.append(
                    {
                        "path": str(copied_metrics),
                        "size": copied_metrics.stat().st_size,
                        "sha256": _sha256(copied_metrics),
                    }
                )

        terminal_state = "succeeded" if process.returncode == 0 else "failed"
        results = {
            "return_code": process.returncode,
            "metrics": metrics,
            "artifacts": artifacts,
        }
        self.workflow.transition(
            EntityType.RUN,
            run.entity_id,
            terminal_state,
            actor_id=actor_id,
            actor_kind=ActorKind.HUMAN,
            data=results,
        )
        self.workflow.transition(
            EntityType.EXPERIMENT,
            experiment_id,
            "awaiting-analysis",
            actor_id=actor_id,
            actor_kind=ActorKind.HUMAN,
            data={"latest_run_id": run.entity_id},
        )
        run_state = self.workflow.store.get(EntityType.RUN.value, run.entity_id)
        manifest_path = run_directory / "run-manifest.json"
        manifest_path.write_text(
            json.dumps(run_state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return RunResult(
            experiment_id,
            run.entity_id,
            process.returncode,
            run_directory,
            manifest_path,
        )
