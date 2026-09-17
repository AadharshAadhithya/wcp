# Project identity and initialization

Every project lives in its own folder and, when appropriate, its own Git
repository. It joins the wider system through a small committed manifest at
`.wcp/project.yaml`.

```yaml
schema_version: 1

project:
  id: 01JABCDEF...
  key: NR
  title: Neural Receiver
  domain: research

git:
  canonical_remote: git@github.com:owner/neural-receiver.git

links:
  vault_entity_id: 01JVAULT...
  plane_workspace_id: 01JWORKSPACE...
  plane_project_id: 01JPLANE...

defaults:
  tracker: mlflow
  artifact_profile: vpn-storage
  policy_profile: research-default
```

Stable IDs are authoritative. Paths, directories, titles, and URLs may change.
The WCP registry joins the stable project ID to its current Git remote, vault
record, Plane project, experiments, and sessions.

`wcp init` is the canonical idempotent entry point for new and existing
repositories. It inspects Git, creates or links the WCP identity, vault record,
and Plane project, writes the manifest, validates the harness adapter and
policy, and prints an Obsidian link that a human may place in `Human/`.

Partial failures remain visible and can be safely repaired with `wcp init` or
`wcp reconcile` without creating duplicates.

Credentials, endpoints, caches, event spools, and machine-local settings do
not enter the repository. They live in user-level WCP configuration and state
directories. Secrets are referenced by profile name.

Initialization is separate from project generation. `wcp init` does not add
application boilerplate. A future `wcp new --template <name>` may create a
small, versioned, human-reviewable skeleton and then invoke `wcp init`.
