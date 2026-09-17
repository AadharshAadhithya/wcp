# Personal AI Infrastructure

This repository contains the generic workflow and supporting software for a
human-owned, agent-native personal operating system. Its first proving ground
is the neural-receiver research project, but its concepts are deliberately not
specific to machine learning or research.

The governing design is documented in
[`docs/philosophy.md`](docs/philosophy.md). Implementation begins with one
vertical slice: take a research question from framing through one reproducible
experiment to a human-approved conclusion, with Plane, the Obsidian vault, and
the operational records kept in sync.

## Status

The philosophy and v1 boundary are agreed. The implementation now includes
project identity, an append-only SQLite event store, deterministic lifecycle
reducers, human approval guards, local experiment provenance, an Obsidian
`Machine/` projector, an idempotent Plane projector, Codex JSONL session
archiving, and a capability-limited MCP server.

The live neural-receiver integration still requires the user's research
repository, Obsidian vault path, and Plane credentials. Product adapters are
configured at runtime; secrets never enter this repository.

## Development

WCP requires Python 3.12 or later. With
[`uv`](https://docs.astral.sh/uv/) installed:

```bash
uv sync --extra dev --extra agent
uv run pytest
```

Initialize a Git repository as a WCP project:

```bash
uv run wcp init --key NR --title "Neural Receiver" --domain research
```

The first invocation discovers the repository's `origin`, generates a stable
ULID, and atomically writes `.wcp/project.yaml`. Repeating `wcp init` validates
and returns the existing identity without changing it. Supplying arguments
that conflict with an existing identity fails explicitly.

Validate a manifest directly with `uv run wcp validate [path]`.

Start the bundled vertical-slice question and experiment design:

```bash
uv run wcp sample neural-receiver
```

See [`docs/getting-started.md`](docs/getting-started.md) for the complete local,
Plane, Obsidian, experiment, Codex-stream, and MCP workflows.
