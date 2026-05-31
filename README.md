# m365-graph-schema-monitor

`m365-graph-schema-monitor` is an offline-first tool for acquiring Microsoft Graph metadata snapshots, inspecting CSDL types, diffing schema changes, and rendering deterministic local reports over fetched snapshots.

## Why this exists

Microsoft Graph schema changes can affect governance, drift detection, and identity/security tooling before those changes are easy to spot in downstream documentation. This project uses deterministic local parsing and diffing, with a tightly constrained snapshot fetch step for public Graph metadata.

## Installation / setup

From repository root:

```bash
python -m pip install -e ".[dev]"
```

## Workflow

Fetch local snapshots, inspect one type, diff snapshots, inventory a snapshot directory, then render a report:

```bash
python -m graph_schema_monitor fetch --profile v1.0 --out /tmp/graph-v1.xml --overwrite
python -m graph_schema_monitor fetch --profile beta --out /tmp/graph-beta.xml --overwrite
python -m graph_schema_monitor inspect --snapshot /tmp/graph-v1.xml --type microsoft.graph.conditionalAccessPolicy
python -m graph_schema_monitor diff --old /tmp/graph-v1.xml --new /tmp/graph-beta.xml --type microsoft.graph.conditionalAccessPolicy
python -m graph_schema_monitor snapshots list --dir /tmp
python -m graph_schema_monitor snapshots validate --dir /tmp
python -m graph_schema_monitor report diff --old /tmp/graph-v1.xml --new /tmp/graph-beta.xml --out /tmp/graph-report.md
```

## Network boundary

`fetch` is intentionally constrained:

- Fixed Graph endpoints only:
  - `https://graph.microsoft.com/v1.0/$metadata`
  - `https://graph.microsoft.com/beta/$metadata`
- No authentication
- No tenant data or permissions
- No arbitrary URLs
- No redirect following
- Sidecar metadata includes only the explicit allowlisted fields

## CLI usage

```bash
python -m graph_schema_monitor fetch --profile v1.0 --out /tmp/graph-v1.xml --overwrite
python -m graph_schema_monitor inspect --snapshot tests/fixtures/schema_old.xml --type microsoft.graph.conditionalAccessPolicy
python -m graph_schema_monitor diff --old tests/fixtures/schema_old.xml --new tests/fixtures/schema_new.xml --type microsoft.graph.conditionalAccessPolicy
python -m graph_schema_monitor diff --old tests/fixtures/schema_old.xml --new tests/fixtures/schema_new.xml --format json
python -m graph_schema_monitor snapshots list --dir /tmp
python -m graph_schema_monitor snapshots validate --dir /tmp
python -m graph_schema_monitor report diff --old /tmp/graph-v1.xml --new /tmp/graph-beta.xml
python -m graph_schema_monitor report diff --old /tmp/graph-v1.xml --new /tmp/graph-beta.xml --format json
```

`report diff` automatically resolves sidecars as `<snapshot-path>.json`, defaults to markdown output, and also supports deterministic JSON output via `--format json`. Use `--out` to write the rendered report to a file atomically; otherwise it prints to stdout. Missing sidecars are allowed for reports and render unknown metadata fields, while malformed or incomplete sidecars still fail validation.

## Testing

```bash
python -m pytest tests/
```

## Known limitations

- Parser scope is intentionally limited to `EntityType` and `ComplexType` declared properties.
- Diff identity is `fully-qualified-type-name + property-name` (declared-only, no inheritance flattening).
- `fetch` only supports the `v1.0` and `beta` public Graph `$metadata` endpoints.
- `report diff` renders unknown metadata when an adjacent sidecar is missing, but malformed or incomplete sidecars still fail.
- No authentication, tenant access, OAuth, MSAL, or Graph SDK integration.
- No arbitrary URL input, scheduler, database, web UI, changelog correlation, canary tenant logic, or AI summarization.

## Roadmap

- Expand parser coverage for additional OData surfaces if needed.
- Add richer output/reporting surfaces while preserving deterministic core behavior.
