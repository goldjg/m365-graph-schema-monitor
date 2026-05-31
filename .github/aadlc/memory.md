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
- No scheduler, background jobs, database, or web UI.
- No changelog correlation, canary-tenant logic, or AI summarization.
- No arbitrary URL fetching or custom URL CLI arguments.
- `fetch-auth` does not acquire, refresh, cache, or store tokens — the caller supplies a valid token via environment variable.

## Architecture summary
- `src/graph_schema_monitor/parser.py` parses local CSDL/XML into a deterministic in-memory snapshot.
- `src/graph_schema_monitor/diff.py` compares two snapshots and emits deterministic change records.
- `src/graph_schema_monitor/fetcher.py` performs constrained snapshot acquisition from fixed Microsoft Graph metadata endpoints and writes local XML plus sidecar metadata.
- `src/graph_schema_monitor/report.py` renders deterministic diff and summary reports over local snapshots.
- `src/graph_schema_monitor/report_filters.py` applies deterministic report filtering and summary aggregation over `DiffChange` values.
- `src/graph_schema_monitor/watchlists.py` loads and validates local watchlist JSON, matches `DiffChange` values with OR-within and AND-across semantics, and renders deterministic markdown/json watchlist reports.
- `src/graph_schema_monitor/versioning.py` performs local-only version/hash/semantic comparison over validated snapshot bundles; it uses `load_snapshot_bundle()`, `diff_snapshots()`, and `SnapshotValidationError` without modifying them. `VersionComparison` dataclass fields: `old_snapshot`, `new_snapshot` (Path); `old_profile`, `new_profile`, `old_fetched_at_utc`, `new_fetched_at_utc` (str|None); `old_sha256`, `new_sha256`, `old_x_ms_schema_version`, `new_x_ms_schema_version` (str, validated non-empty); `schema_version_changed`, `sha256_changed`, `semantic_changes_present` (bool); `semantic_change_count` (int); `classification` (str).
- `src/graph_schema_monitor/source_compare.py` composes `load_snapshot_bundle()`, raw sidecar JSON reads, and `build_version_comparison()` to produce a `SourceComparison` for public-vs-authenticated local snapshot comparison; no network, no env var, no token access.
- `src/graph_schema_monitor/cli.py` provides `fetch`, `fetch-auth`, `inspect`, `diff`, `snapshots`, `report`, `watchlist`, `version`, and `workflow` commands.
- `src/graph_schema_monitor/workflows.py` orchestrates `build_source_comparison()`, `build_version_comparison()`, `build_summary_report()`, optional watchlist functions, and `render_manifest_json()` into a deterministic local evidence bundle; no network, no env var, no token access.
- `tests/fixtures/` stores small hand-authored XML snapshots used for deterministic offline tests.

## Core invariants
- Outbound network access is limited to fixed Microsoft Graph `$metadata` endpoints for `v1.0` and `beta` only; `fetch-auth` adds an `Authorization` header to these same endpoints and does not change the URL allowlist.
- Authenticated tokens flow from env var → memory → HTTP `Authorization` header only; they are never written to disk, logs, or any sidecar field.
- Deterministic output ordering by type then property name.
- Nullable defaults to `true` when absent per OData semantics.
- Diff identity is `fully-qualified-type-name + property-name` using declared properties only.
- Runtime dependencies remain standard-library-only.
- watchlists-local-only: see invariants.yml.
- version-comparison-local-only: see invariants.yml.
- auth-token-not-persisted: see invariants.yml.

- Authenticated sidecar extra fields (`source_kind`, `auth_mode`, `tenant_label`) are not in `ALLOWED_SIDECAR_FIELDS` and are silently ignored (warning only) by `load_snapshot_bundle()`; `source_compare.py` reads them separately via `json.loads()` after bundle validation.
- `source-comparison-local-only`: see invariants.yml.
- `workflow-bundles-local-only`: see invariants.yml.

## Trust boundaries
- User input boundary: CLI paths and type names are untrusted and must be validated for existence/shape.
- Network boundary: only `https://graph.microsoft.com/v1.0/$metadata` and `https://graph.microsoft.com/beta/$metadata` may be fetched, with HTTPS enforcement, redirect rejection, timeout, and content-type validation.
- Token boundary: access tokens are caller-supplied via environment variable; they flow to the `Authorization` header only and must not be persisted in any form.
- File content boundary: XML snapshots are untrusted content and must be parsed without unsafe execution patterns.
- Output boundary: JSON/text output must be deterministic and avoid leaking sensitive context; fetch sidecars must include only the explicit metadata allowlist (authenticated sidecars may additionally include `source_kind`, `auth_mode`, `tenant_label`).

## Known sharp edges
- Graph metadata can express equivalent nullability via absent `Nullable` vs explicit `Nullable="true"`.
- Type strings may use `Collection(...)` wrappers that must be normalized and tracked for shape diffs.
- XML element order is not a stable semantic ordering and should not drive diff ordering.

## Canonical validation commands
- `python -m pytest tests/`
- `python -m graph_schema_monitor fetch --profile v1.0 --out /tmp/graph-metadata.xml --overwrite`
- `python -m graph_schema_monitor inspect --snapshot tests/fixtures/schema_old.xml --type microsoft.graph.conditionalAccessPolicy`
- `python -m graph_schema_monitor diff --old tests/fixtures/schema_old.xml --new tests/fixtures/schema_new.xml --type microsoft.graph.conditionalAccessPolicy`
- `python -m graph_schema_monitor watchlist check --old tests/fixtures/schema_old.xml --new tests/fixtures/schema_new.xml --watchlist tests/fixtures/watchlist_identity.json`

## Current operating assumptions
- Python 3.11+ is the supported runtime target.
- PR2 input snapshots are either local files under user control or files fetched from the fixed Graph metadata allowlist.
- Initial parser scope is EntityType and ComplexType property surfaces, not full OData feature coverage.

## Open questions
- Should future PRs flatten inherited properties for diff reporting or remain declared-only?
- Should future PRs include NavigationProperty diffing as first-class output?
- Should a future live integration test be added behind `GRAPH_SCHEMA_MONITOR_LIVE_TESTS=1` while remaining skipped by default in CI?

## Last updated
2026-05-31 by Copilot (PR9)
