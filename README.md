# m365-graph-schema-monitor

`m365-graph-schema-monitor` is an offline-first tool for inspecting Microsoft Graph-like CSDL snapshots and diffing schema changes.

## Why this exists

Microsoft Graph schema changes can affect governance, drift detection, and identity/security tooling before those changes are easy to spot in downstream documentation. This project starts with deterministic local parsing and diffing so schema evolution is visible from snapshot files alone.

## PR1 scope (intentionally offline)

PR1 includes:

- Local CSDL/XML parsing for `EntityType` and `ComplexType` properties.
- Deterministic property-level schema diffs.
- A minimal CLI (`inspect`, `diff`).
- Hand-authored local fixtures and offline tests.

PR1 does **not** include:

- Live Graph metadata fetch
- Any network access
- Authentication or tenant access
- Scheduler jobs
- Database/storage backends
- Web UI
- Changelog/docs commit correlation
- Canary tenant logic
- AI summarization

## Usage

From repository root:

```bash
python -m graph_schema_monitor inspect --snapshot tests/fixtures/schema_old.xml --type microsoft.graph.conditionalAccessPolicy
python -m graph_schema_monitor diff --old tests/fixtures/schema_old.xml --new tests/fixtures/schema_new.xml --type microsoft.graph.conditionalAccessPolicy
python -m graph_schema_monitor diff --old tests/fixtures/schema_old.xml --new tests/fixtures/schema_new.xml --format json
```

## Testing

```bash
python -m pytest tests/
```

## Known limitations

- Parser scope is intentionally limited to `EntityType` and `ComplexType` declared properties.
- Diff identity is `fully-qualified-type-name + property-name` (declared-only, no inheritance flattening).
- No online collection or changelog correlation in PR1.

## Roadmap (post-PR1)

- Add snapshot acquisition workflow with explicit trust and auth boundaries.
- Expand parser coverage for additional OData surfaces if needed.
- Add richer output/reporting surfaces while preserving deterministic core behavior.
