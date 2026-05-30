<!-- version: 1.0.0 -->
# Durable Architectural Truth Cache

This cache stores durable project truths that should persist beyond a
single task. Update it only when a stable fact, decision, invariant, or
unresolved question should carry forward.

## Project purpose
- Provide an offline-first monitor for Microsoft Graph schema evolution by parsing local CSDL snapshots.
- Detect shape changes in entity and complex types before or independent of vendor changelog timelines.
- Keep PR1 focused on deterministic local parsing/diffing primitives that future online collection can reuse.

## Non-goals
- No live Microsoft Graph fetch in PR1.
- No authentication, tenant access, or permission workflows in PR1.
- No scheduler, background jobs, database, or web UI in PR1.
- No changelog correlation, canary-tenant logic, or AI summarization in PR1.

## Architecture summary
- `src/graph_schema_monitor/parser.py` parses local CSDL/XML into a deterministic in-memory snapshot.
- `src/graph_schema_monitor/diff.py` compares two snapshots and emits deterministic change records.
- `src/graph_schema_monitor/cli.py` provides `inspect` and `diff` commands over local files only.
- `tests/fixtures/` stores small hand-authored XML snapshots used for deterministic offline tests.

## Core invariants
- Offline-only behavior for PR1 (no network calls).
- Deterministic output ordering by type then property name.
- Nullable defaults to `true` when absent per OData semantics.
- Diff identity is `fully-qualified-type-name + property-name` using declared properties only.
- Runtime dependencies remain standard-library-only in PR1.

## Trust boundaries
- User input boundary: CLI paths and type names are untrusted and must be validated for existence/shape.
- File content boundary: XML snapshots are untrusted content and must be parsed without unsafe execution patterns.
- Output boundary: JSON/text output must be deterministic and avoid leaking sensitive context (none expected in PR1).

## Known sharp edges
- Graph metadata can express equivalent nullability via absent `Nullable` vs explicit `Nullable=\"true\"`.
- Type strings may use `Collection(...)` wrappers that must be normalized and tracked for shape diffs.
- XML element order is not a stable semantic ordering and should not drive diff ordering.

## Canonical validation commands
- `python -m pytest tests/`
- `python -m graph_schema_monitor inspect --snapshot tests/fixtures/schema_old.xml --type microsoft.graph.conditionalAccessPolicy`
- `python -m graph_schema_monitor diff --old tests/fixtures/schema_old.xml --new tests/fixtures/schema_new.xml --type microsoft.graph.conditionalAccessPolicy`

## Current operating assumptions
- Python 3.11+ is the supported runtime target.
- PR1 input snapshots are local files under user control.
- Initial parser scope is EntityType and ComplexType property surfaces, not full OData feature coverage.

## Open questions
- Should future PRs flatten inherited properties for diff reporting or remain declared-only?
- Should future PRs include NavigationProperty diffing as first-class output?
- Which online snapshot acquisition workflow (if any) should be introduced post-PR1?

## Last updated
2026-05-30 by Copilot
