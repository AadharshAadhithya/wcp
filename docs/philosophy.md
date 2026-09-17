# A Human-Owned, Agent-Native Personal Operating System

Status: accepted design baseline for v1

## 1. Purpose

This system exists to make a life of research, learning, building, health, and
personal commitments easier to understand and direct. It should preserve the
reasoning behind work, not merely its outputs. It should let agents contribute
without allowing machine-generated activity to overwhelm human thought.

The system is personal infrastructure rather than a collection of isolated
product integrations. Individual tools may be replaced. The durable concepts,
identities, records, and protocols must survive those replacements.

The first implementation will support neural-receiver research. The workflow
itself must remain generic enough to support other projects and life domains.

## 2. Governing principles

### 2.1 Human thought is the point

Automation should remove clerical repetition while preserving the moments in
which a human must form a hypothesis, decide what evidence would matter,
interpret results, and accept responsibility for a conclusion.

Agents may draft, challenge, calculate, search, execute, and propose. They may
not approve a scientific claim or settle a research question.

### 2.2 Durable knowledge and live execution are different kinds of state

Obsidian is the authoritative durable knowledge record: the readable history
of intentions, evidence, decisions, conclusions, and their relationships.

Live leases, locks, heartbeats, queues, and process state require an
operational database. That database is authoritative only for transient
execution. Durable outcomes and histories are projected into the vault.

This is not a competition between two sources of truth. Each owns a distinct
kind of truth.

### 2.3 One fact should have one owner

- Obsidian owns durable reasoning and knowledge.
- Plane owns personal work planning and the operational view of actionable
  work.
- WCP owns live session and workflow state.
- The experiment tracker owns queryable run metrics and parameters.
- The artifact store owns large immutable outputs.
- Git owns source history and versioned project configuration.
- The Session Archive owns complete visible agent conversations and tool logs.

Other systems hold links or projections, not independent hand-maintained
copies.

### 2.4 Raw history is preserved; readable knowledge is curated

Complete visible transcripts, tool results, run logs, and provenance are kept
indefinitely. They do not belong in primary human-readable notes. Agents and a
librarian process may distill raw history into readable summaries, but must
never rewrite or delete the raw record.

### 2.5 The system is replaceable at its edges

Claude Code, Codex, Herdr, Hermes, Plane, MLflow, W&B, and storage products are
adapters around stable internal contracts. No product-specific behavior may
become the only definition of a workflow transition.

### 2.6 Start with a complete narrow loop

The first version proves one useful path end to end. Breadth, dashboards, and
autonomy come after traceability and correctness.

## 3. Life taxonomy

Domains describe **what an outcome serves**:

- **Research:** PhD research, research projects, experiments, papers, and
  research-specific reading.
- **Health:** physical and mental health goals, observations, and routines.
- **Dev:** engineering undertaken for its own sake, tool exploration, and
  infrastructure building.
- **Personal:** relationships, people, home, and personal commitments.
- **Learning:** coursework, skill development, and non-fiction learning not
  primarily serving an active research question.
- **Finance and Admin:** taxes, insurance, subscriptions, purchases, official
  documents, appointments, and household administration.

Practices describe **how work is performed**. Examples include `dev`,
`writing`, `reading`, `experimenting`, `planning`, and `reviewing`.

Classification follows the intended outcome, not the tool. Code written to
answer a research question belongs to Research and carries the `dev` practice.
Automation written to improve health tracking belongs to Health and carries
the `dev` practice.

Each project has one primary domain. Cross-domain relationships are metadata
and links, not duplicated folders.

## 4. Knowledge and memory layers

### 4.1 Obsidian vault

The vault is the human-readable, durable knowledge surface and the primary
dashboard. It contains thought, intent, curated knowledge, research graphs,
approved conclusions, session summaries, and links to external evidence.

### 4.2 Session Archive

The Session Archive stores complete visible human/agent messages, exposed tool
calls and results, approval exchanges, timestamps, subagent relationships, and
compaction boundaries. It does not attempt to capture hidden model reasoning.

Records are immutable, compressed, checksummed, and stored in the artifact
storage layer. A local append-only spool protects against crashes and network
loss. Session close reconciles and seals the archive.

### 4.3 Cross-assistant memory

A Hindsight-style memory service may index the Session Archive and the vault
for retrieval across assistants. It is a derived memory and search layer, not
an authoritative store.

### 4.4 Librarian

The librarian reads machine notes and archived history, then:

- identifies durable knowledge;
- merges repetitive summaries;
- proposes links and destinations;
- detects stale notes and broken references;
- flags conflicting claims;
- refreshes machine-owned indexes;
- proposes archival.

It writes only under `Machine/`. Proposed changes to human-owned knowledge are
review items, never direct edits.

## 5. Vault ownership and structure

Humans may edit the entire vault. Machines may write only under `Machine/`.
Machines never edit `Human/`, including generated blocks within human notes.
Human notes may link to or embed machine-managed notes and dashboards.

`System/` defines schemas, policies, templates, and workflows. Changes to it
require human review.

```text
Human/
  Home.md
  Inbox/
  Journal/
  Planning/
    Vision/
    Goals/
    Reviews/
  Domains/
    Research/
      Projects/
      Papers/
    Health/
    Dev/
    Personal/
    Learning/
    Finance-and-Admin/
  Assets/

Machine/
  Inbox/
  Dashboards/
  Reviews/
  Domains/
    Research/
      Projects/
      Questions/
      Experiments/
    Health/
    Dev/
    Personal/
    Learning/
    Finance-and-Admin/
  Sessions/
  Registry/

System/
  Templates/
  Schemas/
  Policies/
  Workflows/

Archive/
  Legacy/
```

Existing MyNotes content moves unchanged beneath `Archive/Legacy/`.

Human notes use descriptive names and flexible prose. Machine entities have a
globally unique immutable ID, a readable key such as `NR-RQ-001`, a versioned
schema, and validated frontmatter.

Small images intended for reading may live in `Human/Assets/`. Datasets,
checkpoints, raw logs, transcripts, and other large artifacts do not live in
the vault.

## 6. Capture and review

`Human/Inbox/` is a low-friction capture area for human thoughts.
`Machine/Inbox/` contains unclassified imports, agent proposals, and generated
material. Neither is permanent storage.

The global review queue is machine managed and can be embedded in the
human-owned home page:

```text
Machine/Reviews/<review-id>.md
Machine/Dashboards/Review Queue.md
```

Review items include claims awaiting approval, questions ready to settle,
agent blockers, completed work, librarian proposals, experiment analyses,
synchronization conflicts, and stale records.

Their lifecycle is:

```text
pending -> accepted | rejected | deferred | superseded
```

There is one global queue with filtered views for each domain and project.

## 7. Plane's role

Plane manages action, not knowledge. It answers: what deserves attention, who
or what is working on it, what is blocked, and what needs review?

The mapping is:

```text
Plane workspace       -> personal operating system
Plane project         -> concrete project with an outcome
Plane work item       -> actionable unit of work
Plane sub-work item   -> task needed by its parent
Plane dependency      -> blocked-by relationship
Plane cycle           -> optional time-boxed focus period
Plane module          -> optional grouping in a large project
```

For research:

```text
Vault research project -> Plane project
Research question      -> top-level Plane work item
Experiment or task     -> sub-work item
Individual run         -> not a Plane item
Agent session          -> not a Plane item
Claim or evidence      -> not a Plane item
```

Suggested work states are Backlog, Framing, Ready, In Progress, Waiting, Needs
Review, Done, and Cancelled.

Agent comments in Plane are short structured milestones with an outcome,
evidence, blocker or requested decision, next action, and durable links. Raw
agent prose and logs never belong in Plane.

Plane is used by one human. It need not imitate team ceremony.

## 8. Research as a graph of questions

A research project is an evolving graph of research questions. One primary
question is active per project. Supporting questions may run concurrently only
when they are explicitly linked to the primary question and enable useful
parallel work.

Question relationships include:

- `depends-on`: work cannot proceed until another question is settled;
- `raised-by`: evidence or a conclusion generated this question;
- `refines`: the question narrows another;
- `challenges`: the question tests an earlier conclusion;
- `related-to`: a useful non-causal relationship.

Only `depends-on` must be acyclic. The wider knowledge network is a graph.

The vault contains both knowledge and action nodes. Only actionable nodes are
projected into Plane. Hypotheses, existing evidence, claims, and conclusions
remain knowledge records.

### 8.1 Question lifecycle

```text
proposed
  -> framing
  -> ready
  -> investigating
  -> awaiting-analysis
  -> awaiting-decision
  -> settled
```

Exceptional terminal states are `abandoned` and `superseded`. A settled
question may be reopened, but its earlier conclusion remains immutable and is
superseded by a new version.

A question may be settled only when:

- its scope and answer criteria were defined;
- relevant experiments and readings are linked;
- accepted claims cite evidence;
- competing explanations are addressed;
- limitations and confidence are recorded;
- follow-up questions are captured;
- the human owner approves the conclusion.

The human explicitly selects the next primary question.

## 9. Experiments and runs

An experiment is a human-designed test of a hypothesis. A run is one immutable
execution of that design. An experiment may contain pilots, seeds, ablations,
retries, and failed runs. Runs are never overwritten.

### 9.1 Experiment design

Before launch, a normal experiment records:

- the research question and hypothesis;
- why the experiment is worth running now;
- the decision that will change;
- competing explanations;
- predictions for support, refutation, and inconclusive outcomes;
- baselines, controls, confounds, and the smallest informative run;
- metrics and a preregistered analysis plan;
- compute budget and stopping rule;
- linked Plane item, code, configuration, and datasets.

The analysis plan freezes at first launch. Later changes are versioned
amendments with reasons.

Exploratory experiments may use a shorter template, but cannot directly
support an accepted claim. Promising exploratory results must be rerun or
promoted under a complete design.

### 9.2 Run record

The launcher automatically records:

- experiment and run IDs;
- timestamps and state;
- repository, commit, and dirty-tree status;
- resolved configuration and digest;
- available environment and hardware provenance;
- dataset versions and random seeds;
- execution backend and scheduler job ID;
- tracking backend and external run ID;
- artifacts and checksums;
- failures, retries, and deviations.

Normal runs require a clean committed checkout. Explicit exploratory runs may
use a dirty tree only when the complete diff, untracked-file manifest,
dependency state, and tree digest are captured. Such runs are marked
non-reproducible and cannot directly support an accepted claim.

### 9.3 Results, analysis, and claims

Results contain observations: metrics, tables, figures, data-quality checks,
unexpected observations, and protocol deviations. They contain no scientific
inference.

Analysis compares results against predictions, considers alternatives and
confounds, evaluates uncertainty, and identifies further work. Agent-written
analysis is explicitly a draft.

A claim contains its exact scope, supporting and contradicting evidence,
confidence, limitations, approval, and supersession history. Only the human
owner approves a claim.

## 10. Configuration

Each code project keeps versioned source configuration under `configs/`:

```text
configs/
  experiment/
  model/
  data/
  training/
  evaluation/
  environment/
```

The minimal default is YAML composition through OmegaConf with Pydantic
validation at the application boundary. Full Hydra is optional rather than a
requirement.

Every run stores the source config references, exact resolved config, command
line overrides, schema version, and config digest. Secrets are referenced or
redacted, never embedded in run records.

## 11. Experiment tracking and artifacts

WCP creates the canonical experiment and run IDs. A tracking adapter sends
parameters, metrics, and artifact references to exactly one backend per run.

- MLflow is the self-hosted default.
- W&B is an optional backend for quick or collaborative runs.
- Automatic dual logging is forbidden.

The canonical run manifest records the selected backend and external ID or
URL.

Large artifacts live in immutable, content-addressed object storage outside
Git and Obsidian. The initial path is a local spool followed by verified upload
to an S3-compatible service on the VPN storage server. Each artifact records
its producer, type, size, checksum, and storage URI.

Runs may finish while offline, but remain `artifacts-pending` until upload and
checksum verification succeed. Storage uses scoped service credentials,
versioning, TLS, and independent backups.

## 12. Work Control Protocol

The Work Control Protocol (WCP) is the stable, agent-neutral contract between
workers and the workflow system. The name avoids collision with the existing
Agent Client Protocol while acknowledging that humans also perform work.

Herdr is a multiplexer and process orchestrator. Hermes is a possible ambient
agent. Codex and Claude Code are agent harnesses. None owns workflow semantics.

### 12.1 Components

```text
Humans and agent harnesses
          |
     CLI / API / MCP
          |
      WCP service
      |- append-only event log
      |- deterministic state reducers
      |- capability and lease checks
      |- review queue
      |- adapter dispatch
      |
      |- Plane projector
      |- single vault writer
      |- transcript archiver
      |- experiment adapters
      `- notification adapters
```

### 12.2 Event envelope

Every event has a stable ID, session ID, optional work-item ID, actor identity,
event type, timestamp, evidence references, payload, and idempotency key.

Commands include creating and claiming sessions, checkpointing, blocking,
resuming, attaching artifacts, completing, failing, and interrupting.

Routine process, heartbeat, Git, test, job, and tool events are emitted by
wrappers, hooks, or adapters without model tokens. Agents provide semantic
prose only for decisions, blockers, and handoffs.

### 12.3 Harness integration

Normal interactive use relies on globally installed harness plugins:

- lifecycle hooks translate native events;
- an MCP server exposes semantic WCP actions;
- a background component handles transport and heartbeat;
- repository opt-in lives in `.wcp/project.yaml`.

Humans continue to invoke `codex` or `claude` normally.

For managed execution, Herdr is the launcher adapter and supplies scoped
session identity to its children. A generic `wcp run -- <command>` launcher is
only a fallback for unsupported harnesses.

### 12.4 Session modes

- `human`: human work without an active agent;
- `hitl`: a human actively steers one or more agents;
- `delegated`: an agent works independently and returns for review;
- `orchestrated`: a coordinator manages child-agent sessions;
- `background`: a non-conversational job such as training;
- `maintenance`: scheduled indexing, synchronization, or librarian work.

Every session records its initiator, driver, participants, reviewer, optional
parent session, and mode. A session mode may change explicitly, such as HITL
work becoming delegated when the human leaves.

### 12.5 State machines

Separate state machines prevent unrelated concepts from being conflated:

```text
Work item:  backlog -> ready -> active -> blocked -> review -> done
Session:    queued -> claimed -> running -> waiting -> completed/interrupted/failed
Run:        planned -> launched -> running -> succeeded/failed/cancelled -> analyzed
Question:   proposed -> framing -> ready -> investigating -> decision -> settled
```

Active session state is based on registered lifecycle and leases, not on prose
updates from an agent.

### 12.6 Permissions

WCP uses default-deny capability tokens scoped to a session, work item,
repositories, paths, tools, services, compute budget, child-agent budget, and
artifact locations.

Agents cannot write `Human/`, change `System/`, approve claims, settle
questions, rewrite archives, access unrelated secrets, exceed budgets, publish
externally, or merge significant changes without human authority.

Interruptions first request a cooperative checkpoint. After a timeout, the
process is terminated while preserving the local event and transcript spool.

## 13. Synchronization and integrity

The MyNotes repository must be private before sensitive information enters the
new structure.

For v1, private Git provides vault synchronization and audit history:

- `main` is the durable canonical branch;
- human devices and the WCP service use separate working copies;
- the vault writer pulls before changing `Machine/`;
- each transaction creates a small commit containing its WCP event ID;
- non-fast-forward updates trigger re-read and safe retry;
- concurrent human edits are never overwritten;
- conflicts become review items;
- machine commits are structurally prohibited from touching `Human/`;
- encrypted snapshots back up the vault independently of Git.

Obsidian Sync may later improve device convenience, but does not become the
source of truth.

## 14. Goals and planning

Domains are lenses, not isolated lives. Goals connect across four horizons:

- a three-to-five-year vision, reviewed approximately yearly;
- an annual theme backcast from that vision;
- a twelve-week primary quest with limited side quests;
- weekly tactics represented by concrete Plane work items.

Not every domain needs an aggressive quest simultaneously. One domain may be
in focus while others use maintenance goals. Goal changes are expected and are
recorded at review boundaries rather than treated as failure.

Narrative vision and goal reasoning live in `Human/Planning/`. Plane receives
only actionable work derived from those goals. Goal automation is outside v1.

## 15. Notifications

WCP eventually routes events by urgency:

- routine activity appears only on dashboards;
- summaries appear in digests;
- blockers, requested approvals, failures, and completed experiments may
  notify immediately;
- security, runaway compute, corruption, or backup failure are urgent.

Hermes chat channels are intended notification adapters, not dependencies.
Notifications are deferred from v1; the Obsidian review dashboard and CLI are
the initial interfaces.

## 16. Deferred decisions

### 16.1 Reproducible environments

Evaluate Apptainer for local and Slurm multi-GPU execution. Decide image build,
storage, signing, CUDA compatibility, and digest capture. Until resolved, the
launcher records available environment metadata without claiming full
reproducibility.

WCP tracks scheduler jobs but does not replace Slurm.

### 16.2 Object-storage implementation

Select and deploy an S3-compatible service on the VPN storage server after
evaluating its operating system, backup facilities, availability, and desired
immutability features. Product choice is deliberately outside this philosophy.

## 17. Version-one boundary

Version one proves this vertical slice:

```text
Create project
-> frame research question
-> create linked Plane work item
-> start tracked human/agent session
-> design experiment
-> launch one local run
-> capture config, Git SHA, metrics, transcript, and artifacts
-> review results
-> approve a claim
-> settle the question
-> update vault and Plane
```

Included:

- versioned schemas and templates;
- WCP event log and state reducers;
- SQLite operational database;
- CLI;
- single vault writer with Git synchronization;
- Plane adapter;
- global review queue;
- Codex hooks and MCP adapter;
- local Session Archive;
- experiment design and run records;
- OmegaConf and Pydantic configuration;
- MLflow and W&B tracking adapters;
- local artifact spool and an upload interface.

Deferred until the vertical slice works:

- Hermes notifications;
- scheduled librarian automation;
- Claude Code and Herdr adapters;
- Slurm and Apptainer execution;
- production S3 deployment;
- Hindsight indexing;
- automated life goals and domains;
- a rich web UI.

The v1 acceptance test is:

> One real neural-receiver research question can be investigated end to end
> with no manually duplicated metadata and with a readable, reproducible,
> human-approved record in Obsidian.

Codex is the first harness integration. Claude Code and Herdr follow after the
vertical slice is proven.

## 18. What this system refuses to become

- A stream of machine prose mistaken for knowledge.
- A second task manager hidden inside Obsidian.
- A graph database introduced before Markdown links are insufficient.
- An experiment dashboard that omits intent and interpretation.
- A framework that requires agents to spend tokens narrating heartbeats.
- A system in which closing an issue is equivalent to establishing truth.
- An autonomy layer that can silently expand its own authority.
- A product-specific workflow that collapses when one tool is replaced.

The desired outcome is not maximal automation. It is a legible partnership in
which human judgment remains visible, agents remain accountable, and every
important result can be traced back to the question, code, configuration,
evidence, and decision that produced it.
