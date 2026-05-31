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
Add deterministic schema version comparison over existing local snapshots and their adjacent validated sidecars. The comparison answers three questions simultaneously: did x_ms_schema_version change (schema_version_changed), did the raw payload hash change (sha256_changed), and did parsed schema content change (semantic_changes_present).
## Contract status
active
## Non-goals
- Do not add any database, scheduler, background service, or web UI.
- Do not add changelog correlation, documentation correlation, tenant access, authentication, MSAL, Graph SDK usage, or any new network behavior.
- Do not replace or broaden the existing parser, diff, fetch, snapshot inventory, sidecar, or report contracts.
- Do not remove or change current `fetch`, `inspect`, top-level `diff`, `snapshots list`, `snapshots validate`, `report diff`, `report summary`, or `watchlist check` behavior.
- Do not add AI summarization, observability dashboards, cross-tenant reporting, or bundled production watchlist packs.
- Do not introduce new runtime dependencies.
- Do not add authenticated $metadata acquisition.
- Do not merge version compare output into report diff.
- Do not guess or default missing x_ms_schema_version — fail closed.
- Do not add source labels, tenant labels, or public-vs-authenticated comparison.
- Do not add report formats beyond Markdown and JSON.
## Carry-forward rules
- Project-specific facts in `.github/aadlc/memory.md` carry forward only when they describe stable architecture, durable design choices, known sharp edges, or open questions.
- Project-specific trust boundaries in `.github/aadlc/trust-boundaries.md` carry forward because they describe actual repository behaviour and implementation surfaces.
- Project-specific invariants in `.github/aadlc/invariants.yml` carry forward when they describe durable constraints, including the fixed Graph metadata network boundary.
- Completed PR contracts are historical evidence, not active scope.
- Completed PR constraints do not bind future PRs unless they are explicitly promoted to durable invariants or restated in the active PR contract.
## Approved scope
- Add `src/graph_schema_monitor/versioning.py` with `VersionComparison`, `build_version_comparison()`, `classify_version_comparison()`, `render_version_comparison_markdown()`, `render_version_comparison_json()`, and `JSON_VERSION_COMPARISON_REPORT_FIELDS`.
- Extend `src/graph_schema_monitor/cli.py` additively with `version compare` subcommand only.
- Add `tests/test_versioning.py` covering all contract assertions CA-1 through CA-5.
- Update README documentation for the version comparison workflow.
- Refresh this contract and related AADLC artefacts so PR6 scope, stop conditions, escalation triggers, trust-boundary handling, and acceptance criteria are explicitly anchored to version comparison.
## Intentional amendments
- This PR intentionally replaces the prior PR5 active contract; watchlist work is completed history.
- The watchlists-local-only invariant carries forward unchanged.
- A new version-comparison-local-only invariant is appended to invariants.yml.
- Historical PR1 through PR5 work remains evidence only; it is not active implementation scope unless restated here.
## Forbidden scope
- Do not modify the Graph metadata fetch allowlist or permit arbitrary URLs.
- Do not add authentication, tenant access, secrets handling, or any privileged Microsoft 365 access path.
- Do not modify parser.py, diff.py, fetcher.py, snapshots.py, report.py, report_filters.py, or watchlists.py.
- Do not delete or weaken existing tests.
- Do not add persistence beyond existing local snapshot files and adjacent sidecars.
- Do not remove or weaken deterministic ordering guarantees in any existing module.
- Do not change CI scope, add new toolchains, or introduce non-standard-library runtime packages.
- Do not expand parser coverage, add NavigationProperty diffing, or flatten inherited properties.
## Architectural constraints
- Keep `src/graph_schema_monitor/parser.py` as the local CSDL parsing primitive.
- Keep `src/graph_schema_monitor/diff.py` as the deterministic change engine.
- Keep `src/graph_schema_monitor/fetcher.py` as the only networked component.
- Keep `src/graph_schema_monitor/snapshots.py` as the local snapshot and sidecar loading surface.
- Keep `src/graph_schema_monitor/report.py` and `src/graph_schema_monitor/report_filters.py` as existing report primitives.
- Add `src/graph_schema_monitor/versioning.py` as the new local-only version/hash/semantic comparison module.
- Keep CLI output deterministic and file-based.
## Security constraints
- No secrets, credentials, tokens, tenant data, or private customer data may be introduced.
- Do not weaken the fixed Graph metadata network boundary.
- Treat CLI paths and sidecar fields as untrusted inputs; validate before use.
- Sidecar fields sha256 and x_ms_schema_version must be used only for equality comparison and string rendering — no execution, no dynamic import, no eval.
- Fail closed on missing or empty x_ms_schema_version; do not fall back to partial data.
- sha256 values are validated against actual file content by snapshots.py before reaching versioning.py.
- JSON output uses json.dumps() with no dynamic field injection.
- No new secret handling surface is introduced.
## Files expected to change
- `.github/aadlc/current-pr-contract.md`
- `.github/aadlc/memory.md`
- `.github/aadlc/invariants.yml`
- `README.md`
- `src/graph_schema_monitor/cli.py`
- `src/graph_schema_monitor/versioning.py` (new)
- `tests/test_versioning.py` (new)
The following files may be reviewed to preserve existing contracts and invariants:
- `src/graph_schema_monitor/diff.py`
- `src/graph_schema_monitor/fetcher.py`
- `src/graph_schema_monitor/parser.py`
- `src/graph_schema_monitor/report.py`
- `src/graph_schema_monitor/report_filters.py`
- `src/graph_schema_monitor/snapshots.py`
- `src/graph_schema_monitor/watchlists.py`
- `.github/aadlc/trust-boundaries.md`
## Contract assertions
- CA-1: build_version_comparison() raises SnapshotValidationError (exit 2) for each of: absent old sidecar, absent new sidecar, missing/empty old x_ms_schema_version, missing/empty new x_ms_schema_version, and invalid sha256 (propagated from load_snapshot_bundle() hash validation).
- CA-2: classify_version_comparison() maps all eight bool combinations to exact classification strings.
- CA-3: JSON output keys match JSON_VERSION_COMPARISON_REPORT_FIELDS in iteration order; report_type == "version_comparison".
- CA-4: build_version_comparison() opens no network sockets.
- CA-5: All existing tests pass unmodified.
## Tests / validation
- Run `python -m pytest tests/`.
- Confirm all eight classify_version_comparison() combinations are covered by direct unit tests.
- Confirm build_version_comparison() provenance failures each raise SnapshotValidationError individually.
- Confirm invalid sha256 in sidecar surfaces as SnapshotValidationError through load_snapshot_bundle().
- Confirm JSON output field order and report_type value.
- Confirm no-network behaviour with socket monkeypatching.
- Confirm all existing CLI, report, snapshot, watchlist, diff, fetcher, and parser tests pass unchanged.
## Stop conditions
- Version comparison requires changing parser or diff semantics.
- Sidecar validation needs weakening (e.g. allowing None sha256).
- JSON schema compatibility with existing report outputs cannot be preserved.
- Any new runtime dependency appears necessary.
- Any new network behaviour is introduced.
- Authentication, token handling, or tenant access is requested.
- Existing tests would need to be weakened or deleted.
- CLI compatibility (existing commands) cannot be preserved.
- Contract assertions CA-1 through CA-5 cannot be mapped to direct tests.
## Escalation triggers
- Authenticated $metadata acquisition is proposed.
- Version compare output is proposed to merge into report diff.
- Best-effort behaviour when sidecar provenance is missing is proposed.
- Source labels, tenant labels, or public-vs-authenticated comparison is proposed.
- Report formats beyond Markdown and JSON are proposed.
- A dependency not already in pyproject.toml is required.
- Any existing durable invariant requires alteration.
- A new trust-boundary row is needed beyond what is described above.
- NavigationProperty diffing or inherited-property flattening is proposed.
- Parser coverage expansion is proposed.
## Acceptance criteria
- AC-1: python -m pytest tests/ passes with no failures, no deleted tests, no weakened assertions.
- AC-2: version compare exits 0, prints Markdown with all required sections.
- AC-3: version compare --format json exits 0, JSON keys match JSON_VERSION_COMPARISON_REPORT_FIELDS in order.
- AC-4: version compare --format json --out FILE exits 0, writes atomically.
- AC-5: Missing sidecar or x_ms_schema_version exits 2 with clear error.
- AC-6: All eight classification strings exercised by direct unit tests.
- AC-7: No network calls (socket test passes).
- AC-8: All existing PR1–PR5 CLI behaviours intact.
- AC-9: README documents version comparison workflow.
- AC-10: AADLC artefacts reflect PR6; no prior durable state removed.
- AC-11: No new runtime dependencies.
- AC-12: No modifications to parser.py, diff.py, fetcher.py, snapshots.py, report.py, report_filters.py, or watchlists.py.
## Context reset notes
- Mark this contract complete after PR6 version comparison commands are merged.
- Future PRs should create a fresh active contract before adding scheduling, UI, persistence, or any additional comparison surfaces.
- Future substantial or boundary-sensitive tasks should use `.github/aadlc/plans/` rather than large UI prompts.
- Completed PR constraints should be treated as historical evidence unless promoted to durable invariants.
