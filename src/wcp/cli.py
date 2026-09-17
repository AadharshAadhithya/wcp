"""Command line interface for WCP."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from wcp import __version__
from wcp.errors import WcpError
from wcp.manifest import Domain, load_manifest
from wcp.project import MANIFEST_RELATIVE_PATH, initialize_project


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
    return parser


def _manifest_path(path: Path) -> Path:
    candidate = path.expanduser().resolve()
    return candidate if candidate.is_file() else candidate / MANIFEST_RELATIVE_PATH


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
