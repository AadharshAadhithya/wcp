# Getting started with the v1 vertical slice

WCP is local-first. Its SQLite database, session archive, run logs, and copied
configurations live outside the repository by default. Git contains only the
project identity and source configuration.

## 1. Install and initialize

```bash
uv sync --extra dev --extra agent
uv run wcp init --key NR --title "Neural Receiver" --domain research
```

Set `WCP_STATE_DIR` to override the user-level operational state directory.
Use `--db /path/to/state.db` on workflow commands for an isolated test.

## 2. Start the sample question

```bash
uv run wcp sample neural-receiver
```

This idempotently creates:

- `NR-RQ-001`, framed and explicitly selected as the primary ready question;
- `NR-EXP-001`, a preregistered held-out-channel pilot in the ready state.

The command prints their immutable WCP IDs. Inspect them with:

```bash
uv run wcp entity list question
uv run wcp entity list experiment
```

The starter question is deliberately concrete but must be reviewed against the
actual neural-receiver code, datasets, baseline, and available compute before a
real run.

## 3. Run the experiment

Normal runs require a clean committed checkout:

```bash
uv run wcp experiment execute <experiment-id> -- \
  python run_experiment.py --config configs/held_out_channel.yaml
```

Use `--metrics-file results/metrics.json` when the command emits a JSON metrics
object. An explicitly exploratory dirty-tree run is possible with
`--exploratory`; WCP then captures the complete tracked diff, an untracked-file
manifest with hashes, dependency-lock hashes, and a tree digest. Exploratory
runs cannot directly justify an accepted claim.

Each run records its command, Git commit, configuration copies and hashes,
dependency state, logs, metrics, artifact checksums, exit status, and immutable
run manifest beneath the project's user-level WCP state directory.

## 4. Record analysis, claims, and decisions

The generic event commands operate on every entity type:

```bash
uv run wcp entity record experiment <experiment-id> \
  --data @analysis.json --evidence /absolute/path/to/run-manifest.json

uv run wcp entity transition experiment <experiment-id> analyzed \
  --data @analysis.json
```

Create a claim as an agent or human, then move it to `pending-review`. Only a
human CLI invocation can accept or reject it. Acceptance requires exact scope,
supporting evidence, confidence, and limitations.

Only a human may settle a question. Settlement is rejected unless scope,
answer criteria, evidence IDs, accepted claim IDs, competing explanations,
limitations, confidence, follow-up questions, and a conclusion are present.

`--data` accepts either an inline JSON object or `@path/to/file.json`.

## 5. Project into Obsidian

```bash
uv run wcp vault sync /absolute/path/to/MyNotes
```

The projector writes only beneath `Machine/`. It creates research question,
experiment, run, claim, session, and review notes plus
`Machine/Dashboards/Review Queue.md`. It never writes to `Human/` or `System/`.

## 6. Synchronize Plane

Create a Plane personal access token and export it without writing it to Git:

```bash
export PLANE_API_KEY='...'
export PLANE_WORKSPACE_SLUG='my-workspace'
export PLANE_PROJECT_ID='project-uuid'
uv run wcp plane sync
```

`PLANE_BASE_URL` defaults to `https://api.plane.so` and may point to a
self-hosted instance. Questions become top-level work items, experiments become
children, WCP lifecycle states map onto existing Plane state groups, and concise
semantic milestones become comments. Raw transcripts never enter Plane.

## 7. Capture Codex sessions

For a managed non-interactive Codex session:

```bash
uv run wcp codex run --question-id <question-id> -- \
  "Investigate the linked research question and checkpoint meaningful results."
```

WCP launches `codex exec --json`, ingests the JSONL stream, records live session
events, and seals the complete visible stream as a deterministic gzip archive
with a SHA-256 sidecar. A previously captured stream can be ingested with:

```bash
codex exec --json "..." | uv run wcp codex ingest - --mode delegated
```

This adapter covers managed CLI sessions. Desktop sessions require the Codex
host to expose or forward their lifecycle stream; WCP does not claim to capture
events it cannot observe.

## 8. Give Codex semantic WCP tools

Register the local stdio MCP server once:

```bash
codex mcp add wcp \
  --env WCP_PROJECT_PATH=/absolute/path/to/project \
  -- /absolute/path/to/project/.venv/bin/wcp-mcp
```

The server exposes project context and create, record, transition, get, and list
operations. It always acts as an agent. Attempts to approve claims, decide
reviews, or settle research questions are rejected by the workflow layer.

The MCP server uses the official Python MCP SDK's stdio transport. Standard
output is reserved for the protocol.
