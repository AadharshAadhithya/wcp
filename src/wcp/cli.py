"""Command line interface for WCP."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from wcp import __version__
from wcp.archive import SessionArchive
from wcp.codex import CodexStreamIngestor
from wcp.errors import WcpError
from wcp.events import ActorKind, EntityType
from wcp.manifest import Domain, load_manifest
from wcp.plane import PlaneClient, PlaneProjector
from wcp.project import MANIFEST_RELATIVE_PATH, initialize_project
from wcp.runtime import database_path
from wcp.store import EventStore
from wcp.vault import VaultProjector
from wcp.workflow import Workflow


def _add_runtime_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--project-path", type=Path, default=Path.cwd(), help="WCP project root"
    )
    parser.add_argument(
        "--db", type=Path, help="override the user-level state database"
    )


def _add_actor_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--actor", default="human:owner")
    parser.add_argument(
        "--actor-kind",
        choices=[kind.value for kind in ActorKind],
        default=ActorKind.HUMAN.value,
    )
    parser.add_argument("--session-id")
    parser.add_argument("--idempotency-key")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wcp", description="Work Control Protocol")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="initialize or inspect project identity")
    init.add_argument("path", nargs="?", type=Path, default=Path.cwd())
    init.add_argument("--key", help="short readable project key, such as NR")
    init.add_argument("--title", help="human-readable project title")
    init.add_argument("--domain", choices=[domain.value for domain in Domain])
    init.add_argument("--remote", help="canonical Git remote; defaults to origin")
    init.add_argument("--vault-entity-id")
    init.add_argument("--plane-workspace-id")
    init.add_argument("--plane-project-id")

    validate = commands.add_parser("validate", help="validate a project manifest")
    validate.add_argument("path", nargs="?", type=Path, default=Path.cwd())

    entity = commands.add_parser("entity", help="record workflow entity events")
    entity_commands = entity.add_subparsers(dest="entity_command", required=True)
    create = entity_commands.add_parser("create", help="create a workflow entity")
    create.add_argument("entity_type", choices=[item.value for item in EntityType])
    create.add_argument("--data", required=True, help="JSON object with entity data")
    create.add_argument("--entity-id")
    _add_runtime_arguments(create)
    _add_actor_arguments(create)

    transition = entity_commands.add_parser(
        "transition", help="apply a validated lifecycle transition"
    )
    transition.add_argument("entity_type", choices=[item.value for item in EntityType])
    transition.add_argument("entity_id")
    transition.add_argument("target")
    transition.add_argument("--data", default="{}", help="JSON object to record")
    _add_runtime_arguments(transition)
    _add_actor_arguments(transition)

    record = entity_commands.add_parser("record", help="record semantic entity data")
    record.add_argument("entity_type", choices=[item.value for item in EntityType])
    record.add_argument("entity_id")
    record.add_argument("--data", required=True, help="JSON object to merge")
    record.add_argument("--evidence", action="append", default=[])
    _add_runtime_arguments(record)
    _add_actor_arguments(record)

    show = entity_commands.add_parser("show", help="show current projected state")
    show.add_argument("entity_type", choices=[item.value for item in EntityType])
    show.add_argument("entity_id")
    _add_runtime_arguments(show)

    list_entities = entity_commands.add_parser("list", help="list projected entities")
    list_entities.add_argument(
        "entity_type", choices=[item.value for item in EntityType]
    )
    _add_runtime_arguments(list_entities)

    vault = commands.add_parser("vault", help="project durable state into Obsidian")
    vault_commands = vault.add_subparsers(dest="vault_command", required=True)
    vault_sync = vault_commands.add_parser("sync", help="write Machine/ notes")
    vault_sync.add_argument("vault_path", type=Path)
    _add_runtime_arguments(vault_sync)

    plane = commands.add_parser("plane", help="synchronize actionable work with Plane")
    plane_commands = plane.add_subparsers(dest="plane_command", required=True)
    plane_sync = plane_commands.add_parser(
        "sync", help="project work items and milestones"
    )
    plane_sync.add_argument(
        "--base-url", default=os.environ.get("PLANE_BASE_URL", "https://api.plane.so")
    )
    plane_sync.add_argument(
        "--workspace-slug", default=os.environ.get("PLANE_WORKSPACE_SLUG")
    )
    plane_sync.add_argument(
        "--plane-project-id", default=os.environ.get("PLANE_PROJECT_ID")
    )
    _add_runtime_arguments(plane_sync)

    codex = commands.add_parser("codex", help="capture Codex JSONL session streams")
    codex_commands = codex.add_subparsers(dest="codex_command", required=True)
    codex_ingest = codex_commands.add_parser("ingest", help="ingest a JSONL stream")
    codex_ingest.add_argument("file", nargs="?", default="-")
    codex_ingest.add_argument(
        "--mode",
        choices=[
            "human",
            "hitl",
            "delegated",
            "orchestrated",
            "background",
            "maintenance",
        ],
        default="hitl",
    )
    codex_ingest.add_argument("--question-id")
    codex_ingest.add_argument("--echo", action="store_true")
    _add_runtime_arguments(codex_ingest)

    codex_run = codex_commands.add_parser(
        "run", help="run `codex exec --json` and archive its stream"
    )
    codex_run.add_argument(
        "--mode",
        choices=["hitl", "delegated", "orchestrated", "background", "maintenance"],
        default="delegated",
    )
    codex_run.add_argument("--question-id")
    _add_runtime_arguments(codex_run)
    codex_run.add_argument("codex_args", nargs=argparse.REMAINDER)
    return parser


def _manifest_path(path: Path) -> Path:
    candidate = path.expanduser().resolve()
    return candidate if candidate.is_file() else candidate / MANIFEST_RELATIVE_PATH


def _runtime(args: argparse.Namespace) -> tuple[Workflow, EventStore]:
    manifest = load_manifest(_manifest_path(args.project_path))
    store = EventStore(database_path(manifest.project.id, args.db))
    return Workflow(store, manifest.project.id), store


def _json_object(raw: str) -> dict[str, object]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON: {error.msg}") from error
    if not isinstance(value, dict):
        raise ValueError("data must be a JSON object")
    return value


def run(arguments: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(arguments)

    try:
        if args.command == "init":
            result = initialize_project(
                args.path,
                key=args.key,
                title=args.title,
                domain=Domain(args.domain) if args.domain else None,
                remote=args.remote,
                vault_entity_id=args.vault_entity_id,
                plane_workspace_id=args.plane_workspace_id,
                plane_project_id=args.plane_project_id,
            )
            action = (
                "Created"
                if result.created
                else "Updated"
                if result.updated
                else "Validated existing"
            )
            print(f"{action} WCP project {result.manifest.project.key}")
            print(f"Project ID: {result.manifest.project.id}")
            print(f"Manifest: {result.manifest_path}")
            return 0

        if args.command == "entity":
            workflow, store = _runtime(args)
            entity_type = EntityType(args.entity_type)
            if args.entity_command == "create":
                event = workflow.create(
                    entity_type,
                    _json_object(args.data),
                    actor_id=args.actor,
                    actor_kind=ActorKind(args.actor_kind),
                    entity_id=args.entity_id,
                    session_id=args.session_id,
                    idempotency_key=args.idempotency_key,
                )
                print(event.entity_id)
                return 0
            if args.entity_command == "transition":
                event = workflow.transition(
                    entity_type,
                    args.entity_id,
                    args.target,
                    actor_id=args.actor,
                    actor_kind=ActorKind(args.actor_kind),
                    data=_json_object(args.data),
                    session_id=args.session_id,
                    idempotency_key=args.idempotency_key,
                )
                print(
                    json.dumps(store.get(entity_type.value, event.entity_id), indent=2)
                )
                return 0
            if args.entity_command == "record":
                event = workflow.record(
                    entity_type,
                    args.entity_id,
                    _json_object(args.data),
                    actor_id=args.actor,
                    actor_kind=ActorKind(args.actor_kind),
                    session_id=args.session_id,
                    evidence=tuple(args.evidence),
                    idempotency_key=args.idempotency_key,
                )
                print(
                    json.dumps(store.get(entity_type.value, event.entity_id), indent=2)
                )
                return 0
            if args.entity_command == "show":
                aggregate = store.get(entity_type.value, args.entity_id)
                if aggregate is None:
                    raise ValueError(f"No {entity_type.value} {args.entity_id}")
                print(json.dumps(aggregate, indent=2))
                return 0
            print(
                json.dumps(store.list(entity_type.value, workflow.project_id), indent=2)
            )
            return 0

        if args.command == "vault":
            workflow, store = _runtime(args)
            written = VaultProjector(args.vault_path).sync(store, workflow.project_id)
            print(f"Projected {len(written)} note(s) into {args.vault_path.resolve()}")
            return 0

        if args.command == "plane":
            workflow, store = _runtime(args)
            manifest = load_manifest(_manifest_path(args.project_path))
            api_key = os.environ.get("PLANE_API_KEY")
            plane_project_id = args.plane_project_id or manifest.links.plane_project_id
            if not api_key:
                raise ValueError("PLANE_API_KEY is required")
            if not args.workspace_slug:
                raise ValueError("--workspace-slug or PLANE_WORKSPACE_SLUG is required")
            if not plane_project_id:
                raise ValueError(
                    "--plane-project-id, PLANE_PROJECT_ID, "
                    "or a manifest link is required"
                )
            client = PlaneClient(
                base_url=args.base_url,
                api_key=api_key,
                workspace_slug=args.workspace_slug,
                project_id=plane_project_id,
            )
            counts = PlaneProjector(client).sync(store, workflow.project_id)
            print(json.dumps(counts, indent=2))
            return 0

        if args.command == "codex":
            workflow, store = _runtime(args)
            ingestor = CodexStreamIngestor(
                workflow, SessionArchive(store.path.parent / "session-archive")
            )
            if args.codex_command == "ingest":
                if args.file == "-":
                    result = ingestor.ingest(
                        sys.stdin,
                        mode=args.mode,
                        question_id=args.question_id,
                        echo=args.echo,
                    )
                else:
                    with Path(args.file).open(encoding="utf-8") as stream:
                        result = ingestor.ingest(
                            stream,
                            mode=args.mode,
                            question_id=args.question_id,
                            echo=args.echo,
                        )
            else:
                codex_args = args.codex_args
                if codex_args and codex_args[0] == "--":
                    codex_args = codex_args[1:]
                if not codex_args:
                    raise ValueError(
                        "codex run requires a prompt or Codex arguments after --"
                    )
                try:
                    process = subprocess.Popen(  # noqa: S603
                        ["codex", "exec", "--json", *codex_args],  # noqa: S607
                        cwd=args.project_path,
                        stdout=subprocess.PIPE,
                        text=True,
                        bufsize=1,
                    )
                except OSError as error:
                    raise ValueError(f"Could not start Codex: {error}") from error
                if process.stdout is None:  # pragma: no cover - required by PIPE
                    raise RuntimeError("Codex stdout pipe was not created")
                result = ingestor.ingest(
                    process.stdout,
                    mode=args.mode,
                    question_id=args.question_id,
                    echo=True,
                    successful=lambda: process.wait() == 0,
                )
            print(
                json.dumps(
                    {
                        "session_id": result.session_id,
                        "event_count": result.event_count,
                        "archive_path": str(result.archive_path),
                        "sha256": result.checksum,
                    },
                    indent=2,
                )
            )
            return 0

        manifest_path = _manifest_path(args.path)
        manifest = load_manifest(manifest_path)
        print(
            f"Valid WCP project {manifest.project.key} "
            f"({manifest.project.id}), schema v{manifest.schema_version}"
        )
        return 0
    except WcpError as error:
        parser.exit(2, f"wcp: error: {error}\n")
    except ValueError as error:
        parser.exit(2, f"wcp: error: {error}\n")


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":  # pragma: no cover
    main()
