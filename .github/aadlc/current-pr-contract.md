<!-- version: 1.1.0 -->
# Current PR Contract
This contract constrains implementation scope for the active PR. Update
it when scope is explicitly amended. If a requested action falls outside
approved scope, stop and escalate before proceeding.
Use this contract to distinguish active PR constraints, completed PR
constraints, durable invariants, and intentional amendments. Completed
PR constraints are historical evidence unless they are explicitly
promoted to durable invariants.
## Goal
Add a `workflow compare-public-auth` CLI command that bundles existing
public-vs-authenticated Graph `$metadata` comparison outputs into a
deterministic local evidence report directory. The command consumes
existing local snapshot files only, reuses existing PR6–PR8 primitives,
and writes a deterministic manifest. No new network behaviour, no
authentication, no token handling.
## Contract status
active
## Non-goals
- Do not add any new network calls.
- Do not add fetch or fetch-auth changes unless a strict compatibility bug is found and approved.
- Do not add MSAL, device code flow, browser login, client secret, certificate credential, token acquisition, token cache, token persistence, or tenant discovery.
- Do not add any Graph SDK or arbitrary URL fetching.
- Do not add sovereign cloud support, scheduler, database, or web UI.
- Do not add changelog/docs correlation or AI summarisation.
- Do not add new runtime dependencies (standard library only).
- Do not broaden parser/diff/fetch/version/source/watchlist semantics.
- Do not add NavigationProperty diffing or inherited-property flattening.
- Do not replace or broaden the existing `fetch`, `fetch-auth`, `inspect`, `diff`, `snapshots list`, `snapshots validate`, `report diff`, `report summary`, `watchlist check`, `version compare`, or `version compare-sources` contracts.
## Carry-forward rules
- Project-specific facts in `.github/aadlc/memory.md` carry forward only when they describe stable architecture, durable design choices, known sharp edges, or open questions.
- Project-specific trust boundaries in `.github/aadlc/trust-boundaries.md` carry forward because they describe actual repository behaviour and implementation surfaces.
- Project-specific invariants in `.github/aadlc/invariants.yml` carry forward when they describe durable constraints.
- Completed PR contracts are historical evidence, not active scope.
## Approved scope
- Add `src/graph_schema_monitor/workflows.py` with `WorkflowBundle` dataclass, `build_compare_public_auth_bundle()`, `render_manifest_json()`, and `_write_text_file_atomic()`.
- Extend `src/graph_schema_monitor/cli.py` additively with `workflow compare-public-auth` subcommand.
- Add `tests/test_workflows.py` with CA-1 through CA-5 coverage.
- Update `README.md` with a "Local evidence workflow bundle" section.
- Refresh this contract and AADLC artefacts for PR9 scope.
## Intentional amendments
- This PR intentionally replaces the prior PR8 active contract; source comparison work is completed history.
- A new `workflow-bundles-local-only` invariant is added to `invariants.yml`.
- Historical PR1 through PR8 work remains evidence only; it is not active implementation scope unless restated here.
## Forbidden scope
- Do not modify `fetcher.py`, `snapshots.py`, `versioning.py`, `source_compare.py`, `parser.py`, `diff.py`, `report.py`, `report_filters.py`, or `watchlists.py` unless a strict compatibility bug is found.
- Do not add any new runtime dependencies.
- Do not delete or weaken existing tests.
- Do not add persistence beyond existing local snapshot files and adjacent sidecars.
- Do not remove or weaken deterministic ordering guarantees in any existing module.
- Do not change CI scope or add new toolchains.
## Architectural constraints
- Keep `src/graph_schema_monitor/workflows.py` as a thin orchestration layer over existing primitives.
- `build_compare_public_auth_bundle()` must not call `fetch_snapshot()` or `fetch_authenticated_snapshot()`.
- `build_compare_public_auth_bundle()` must not read environment variables or open network sockets.
- No wall-clock timestamps may be introduced into generated reports or the manifest.
- `_write_text_file_atomic()` in `workflows.py` must be a private helper; `_write_output_file()` in `cli.py` must not be imported into `workflows.py` (import cycle prevention).
## Security constraints
- `workflows.py` must not read any environment variables.
- `workflows.py` must not make any network calls.
- `workflows.py` must not call `fetch_snapshot()` or `fetch_authenticated_snapshot()`.
- Output files must not include token data, token env var names, raw headers, tenant IDs, user IDs, app IDs, or claims.
- Manifest must not include wall-clock timestamps.
## Files expected to change
- `.github/aadlc/current-pr-contract.md`
- `.github/aadlc/memory.md`
- `.github/aadlc/invariants.yml`
- `.github/aadlc/trust-boundaries.md`
- `README.md`
- `src/graph_schema_monitor/cli.py`
- `src/graph_schema_monitor/workflows.py` (new)
- `tests/test_workflows.py` (new)
The following files must not change:
- `src/graph_schema_monitor/diff.py`
- `src/graph_schema_monitor/fetcher.py`
- `src/graph_schema_monitor/parser.py`
- `src/graph_schema_monitor/report.py`
- `src/graph_schema_monitor/report_filters.py`
- `src/graph_schema_monitor/snapshots.py`
- `src/graph_schema_monitor/source_compare.py`
- `src/graph_schema_monitor/versioning.py`
- `src/graph_schema_monitor/watchlists.py`
## Contract assertions
- CA-1: Without `--watchlist`, the workflow writes exactly 7 files; with `--watchlist`, exactly 9 files. Output filenames are stable.
- CA-2: `manifest.json` has exactly the approved top-level fields in stable order. Output paths in `outputs` are relative filenames. `watchlist` is `null` when no watchlist is supplied.
- CA-3: If any planned output exists and `--overwrite` is not supplied, the command fails before writing anything. Render failures before the write phase leave no partial bundle files.
- CA-4: Generated `source-comparison.json` matches `render_source_comparison_json(build_source_comparison(...))`. Generated `version-comparison.json` matches `render_version_comparison_json(build_version_comparison(...))`. Generated `summary.json` matches `build_summary_report(..., output_format="json")`. Watchlist output matches existing watchlist renderer.
- CA-5: Workflow command performs no network calls, does not read tokens or environment variables, does not call `fetch_snapshot()` or `fetch_authenticated_snapshot()`.
## Tests / validation
- Run `python -m pytest tests/`.
- Confirm all existing tests pass unchanged.
- Confirm CA-1 through CA-5 are each covered by direct unit tests in `tests/test_workflows.py`.
## Stop conditions
- Workflow bundle requires changing `fetcher.py`, `source_compare.py`, `versioning.py`, `report.py`, or `watchlists.py`.
- Any network call becomes necessary.
- Any token/env access becomes necessary.
- Atomic/no-partial-write behaviour cannot be implemented simply.
- Existing tests would need weakening.
## Acceptance criteria
- AC-1: `python -m pytest tests/` passes with no failures, no deleted tests.
- AC-2: `workflow compare-public-auth` bundles outputs from existing local primitives.
- AC-3: Bundle without watchlist contains exactly 7 files; with watchlist exactly 9 files.
- AC-4: `manifest.json` has approved stable top-level fields.
- AC-5: Existing planned outputs cause failure unless `--overwrite`.
- AC-6: No partial outputs left after pre-write failures.
- AC-7: Generated reports match direct renderer output.
- AC-8: No network calls introduced.
- AC-9: No token/env access introduced.
- AC-10: No new runtime dependencies.
- AC-11: README documents the workflow bundle.
- AC-12: AADLC artefacts reflect PR9 scope without removing prior durable state.
- AC-13: All existing PR1–PR8 commands and tests pass unchanged.
## Context reset notes
- Mark this contract complete after PR9 `workflow compare-public-auth` command is merged.
- Future PRs should create a fresh active contract before adding scheduling, UI, persistence, live comparison, or any additional acquisition surfaces.
- Future substantial or boundary-sensitive tasks should use `.github/aadlc/plans/` rather than large UI prompts.

