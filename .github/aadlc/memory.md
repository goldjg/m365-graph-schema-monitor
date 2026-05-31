<!-- version: 1.0.0 -->
# Durable Architectural Truth Cache

This cache stores durable project truths that should persist beyond a
single task. Update it only when a stable fact, decision, invariant, or
unresolved question should carry forward.

## Project purpose
- Provide an offline-first monitor for Microsoft Graph schema evolution by parsing local CSDL snapshots.
- Detect shape changes in entity and complex types before or independent of vendor changelog timelines.
- Keep deterministic local parsing/diffing primitives reusable for constrained snapshot acquisition workflows.

## Non-goals
- No authentication, tenant access, or permission workflows in PR2.
- No scheduler, background jobs, database, or web UI in PR2.
- No changelog correlation, canary-tenant logic, or AI summarization in PR2.
- No arbitrary URL fetching or custom URL CLI arguments in PR2.

## Architecture summary
- `src/graph_schema_monitor/parser.py` parses local CSDL/XML into a deterministic in-memory snapshot.
- `src/graph_schema_monitor/diff.py` compares two snapshots and emits deterministic change records.
- `src/graph_schema_monitor/fetcher.py` performs constrained snapshot acquisition from fixed Microsoft Graph metadata endpoints and writes local XML plus sidecar metadata.
- `src/graph_schema_monitor/report.py` renders deterministic diff and summary reports over local snapshots.
- `src/graph_schema_monitor/report_filters.py` applies deterministic report filtering and summary aggregation over `DiffChange` values.
- `src/graph_schema_monitor/cli.py` provides `fetch`, `inspect`, `diff`, `snapshots`, and `report` commands.
- `tests/fixtures/` stores small hand-authored XML snapshots used for deterministic offline tests.

## Core invariants
- Outbound network access in PR2 is limited to fixed Microsoft Graph `$metadata` endpoints for `v1.0` and `beta` only.
- Deterministic output ordering by type then property name.
- Nullable defaults to `true` when absent per OData semantics.
- Diff identity is `fully-qualified-type-name + property-name` using declared properties only.
- Runtime dependencies remain standard-library-only in PR2.

## Trust boundaries
- User input boundary: CLI paths and type names are untrusted and must be validated for existence/shape.
- Network boundary: only `https://graph.microsoft.com/v1.0/$metadata` and `https://graph.microsoft.com/beta/$metadata` may be fetched, with HTTPS enforcement, redirect rejection, timeout, and content-type validation.
- File content boundary: XML snapshots are untrusted content and must be parsed without unsafe execution patterns.
- Output boundary: JSON/text output must be deterministic and avoid leaking sensitive context; fetch sidecars must include only the explicit metadata allowlist.

## Known sharp edges
- Graph metadata can express equivalent nullability via absent `Nullable` vs explicit `Nullable="true"`.
- Type strings may use `Collection(...)` wrappers that must be normalized and tracked for shape diffs.
- XML element order is not a stable semantic ordering and should not drive diff ordering.

## Canonical validation commands
- `python -m pytest tests/`
- `python -m graph_schema_monitor fetch --profile v1.0 --out /tmp/graph-metadata.xml --overwrite`
- `python -m graph_schema_monitor inspect --snapshot tests/fixtures/schema_old.xml --type microsoft.graph.conditionalAccessPolicy`
- `python -m graph_schema_monitor diff --old tests/fixtures/schema_old.xml --new tests/fixtures/schema_new.xml --type microsoft.graph.conditionalAccessPolicy`

## Current operating assumptions
- Python 3.11+ is the supported runtime target.
- PR2 input snapshots are either local files under user control or files fetched from the fixed Graph metadata allowlist.
- Initial parser scope is EntityType and ComplexType property surfaces, not full OData feature coverage.

## Open questions
- Should future PRs flatten inherited properties for diff reporting or remain declared-only?
- Should future PRs include NavigationProperty diffing as first-class output?
- Should a future live integration test be added behind `GRAPH_SCHEMA_MONITOR_LIVE_TESTS=1` while remaining skipped by default in CI?

## Last updated
2026-05-31 by Copilot
