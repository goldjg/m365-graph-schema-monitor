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
Add a first-class `version compare-sources` CLI command that compares a local
public unauthenticated Graph `$metadata` snapshot against a local authenticated
Graph `$metadata` snapshot. The command consumes existing local snapshot files
only, reuses the PR6 version comparison primitives, and validates provenance
via adjacent sidecar JSON. No new network behaviour, no authentication, no
token handling.
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
- Do not broaden parser/diff/fetch/version/watchlist semantics.
- Do not add NavigationProperty diffing or inherited-property flattening.
- Do not replace or broaden the existing `fetch`, `fetch-auth`, `inspect`, `diff`, `snapshots list`, `snapshots validate`, `report diff`, `report summary`, `watchlist check`, or `version compare` contracts.
## Carry-forward rules
- Project-specific facts in `.github/aadlc/memory.md` carry forward only when they describe stable architecture, durable design choices, known sharp edges, or open questions.
- Project-specific trust boundaries in `.github/aadlc/trust-boundaries.md` carry forward because they describe actual repository behaviour and implementation surfaces.
- Project-specific invariants in `.github/aadlc/invariants.yml` carry forward when they describe durable constraints.
- Completed PR contracts are historical evidence, not active scope.
## Approved scope
- Add `src/graph_schema_monitor/source_compare.py` with `SourceComparison` dataclass, `build_source_comparison()`, `render_source_comparison_markdown()`, `render_source_comparison_json()`, and provenance helpers.
- Extend `src/graph_schema_monitor/cli.py` additively with `version compare-sources` subcommand.
- Add `tests/test_source_compare.py` with all provenance, profile, version comparison, JSON/Markdown, CLI, and local-only tests.
- Update `README.md` with a "Public vs authenticated metadata comparison" section.
- Refresh this contract and AADLC artefacts for PR8 scope.
## Intentional amendments
- This PR intentionally replaces the prior PR7 active contract; authenticated fetch work is completed history.
- A new `source-comparison-local-only` invariant is added to `invariants.yml`.
- Historical PR1 through PR7 work remains evidence only; it is not active implementation scope unless restated here.
## Forbidden scope
- Do not modify `fetcher.py`, `snapshots.py`, `versioning.py`, `parser.py`, `diff.py`, `report.py`, `report_filters.py`, or `watchlists.py` unless a strict compatibility bug is found.
- Do not add any new runtime dependencies.
- Do not delete or weaken existing tests.
- Do not add persistence beyond existing local snapshot files and adjacent sidecars.
- Do not remove or weaken deterministic ordering guarantees in any existing module.
- Do not change CI scope or add new toolchains.
## Architectural constraints
- Keep `src/graph_schema_monitor/source_compare.py` as a thin composition layer over existing primitives.
- `build_source_comparison()` must call `load_snapshot_bundle()` for validation before reading raw sidecar JSON for provenance extras.
- `build_source_comparison()` must call `build_version_comparison()` for version/content/semantic comparison.
- No network access, no env var reads, no token handling in `source_compare.py`.
## Security constraints
- `source_compare.py` must not read any environment variables.
- `source_compare.py` must not make any network calls.
- `source_compare.py` must not call `fetch_snapshot()` or `fetch_authenticated_snapshot()`.
- Sidecar extra-field reading is a local read-only operation; no sidecar files are altered.
- JSON output must not include token data, token env var names, raw headers, request metadata, tenant IDs, user IDs, app IDs, or claims.
- `tenant_label` is an opaque display string; it must not be interpreted as authoritative tenant identity.
## Files expected to change
- `.github/aadlc/current-pr-contract.md`
- `.github/aadlc/memory.md`
- `.github/aadlc/invariants.yml`
- `README.md`
- `src/graph_schema_monitor/cli.py`
- `src/graph_schema_monitor/source_compare.py` (new)
- `tests/test_source_compare.py` (new)
The following files must not change:
- `src/graph_schema_monitor/diff.py`
- `src/graph_schema_monitor/fetcher.py`
- `src/graph_schema_monitor/parser.py`
- `src/graph_schema_monitor/report.py`
- `src/graph_schema_monitor/report_filters.py`
- `src/graph_schema_monitor/snapshots.py`
- `src/graph_schema_monitor/versioning.py`
- `src/graph_schema_monitor/watchlists.py`
## Contract assertions
- CA-1: Public side accepts missing source_kind as public_graph_metadata; public side rejects source_kind == authenticated_graph_metadata; authenticated side requires source_kind == authenticated_graph_metadata and auth_mode == env_token.
- CA-2: Profile mismatch fails with exit code 2 by default; profile mismatch succeeds with --allow-profile-mismatch and emits a warning.
- CA-3: Source comparison reuses PR6 version comparison results; JSON output values for schema_version_changed, sha256_changed, semantic_change_count, semantic_changes_present, and version_classification match build_version_comparison(public, authenticated).
- CA-4: version compare-sources --format json produces exactly the approved top-level fields in stable order.
- CA-5: compare-sources performs no network calls, does not read tokens or environment variables, does not call fetch or fetch-auth.
## Tests / validation
- Run `python -m pytest tests/`.
- Confirm all existing tests pass unchanged.
- Confirm CA-1 through CA-5 are each covered by direct unit tests in `tests/test_source_compare.py`.
## Stop conditions
- Source comparison requires changing fetcher.py, snapshots.py, or versioning.py.
- Existing sidecar extra-field warning behaviour blocks implementation.
- Token access, token env vars, or auth handling becomes necessary.
- Any network call becomes necessary.
- Tests would need live network access.
## Acceptance criteria
- AC-1: `python -m pytest tests/` passes with no failures, no deleted tests.
- AC-2: `version compare-sources` compares two local snapshots only.
- AC-3: Public side missing source_kind is accepted as legacy public metadata.
- AC-4: Authenticated side requires source_kind=authenticated_graph_metadata and auth_mode=env_token.
- AC-5: Profile mismatch fails by default (exit 2); allowed with --allow-profile-mismatch (exit 0 + warning).
- AC-6: JSON output has approved stable top-level fields.
- AC-7: Markdown output has required sections.
- AC-8: Source comparison reuses PR6 version comparison output.
- AC-9: No network calls introduced.
- AC-10: No token/env access introduced.
- AC-11: No new runtime dependencies.
- AC-12: README documents the source comparison workflow.
- AC-13: AADLC artefacts reflect PR8 scope without removing prior durable state.
## Context reset notes
- Mark this contract complete after PR8 `version compare-sources` command is merged.
- Future PRs should create a fresh active contract before adding scheduling, UI, persistence, live comparison, or any additional acquisition surfaces.
- Future substantial or boundary-sensitive tasks should use `.github/aadlc/plans/` rather than large UI prompts.
