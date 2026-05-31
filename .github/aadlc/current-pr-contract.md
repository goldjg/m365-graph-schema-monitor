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
Implement PR3 local snapshot inventory and deterministic local diff report rendering over already-fetched snapshots while preserving the existing offline parser/diff/fetch core and trust boundaries.
## Contract status
active
## Non-goals
- Do not add any database, scheduler, background service, or web UI.
- Do not add changelog correlation, tenant access, authentication, MSAL, Graph SDK usage, or any new network behavior.
- Do not replace or broaden the existing parser/diff/fetch sidecar contract.
- Do not remove or change current `fetch`, `inspect`, or top-level `diff` behavior except where new nested commands coexist alongside them.
- Do not add AI summarization, observability dashboards, or cross-tenant reporting.
- Do not introduce new runtime dependencies.
## Carry-forward rules
- Project-specific facts in `.github/aadlc/memory.md` carry forward only when they describe stable architecture, durable design choices, known sharp edges, or open questions.
- Project-specific trust boundaries in `.github/aadlc/trust-boundaries.md` carry forward because they describe actual repository behaviour and implementation surfaces.
- Project-specific invariants in `.github/aadlc/invariants.yml` carry forward when they describe durable constraints, including the fixed Graph metadata network boundary.
- Completed PR contracts are historical evidence, not active scope.
- Completed PR constraints do not bind future PRs unless they are explicitly promoted to durable invariants or restated in the active PR contract.
- Reusable instruction-pack guidance may be synced from `coding-agent-baselines` when it improves AADLCv2 governance without erasing repository-specific state.
## Approved scope
- Update `src/graph_schema_monitor/cli.py` to add nested `snapshots` and `report` command groups while preserving existing top-level `fetch`, `inspect`, and `diff` commands.
- Add file-based snapshot inventory logic for `snapshots list --dir <DIR>`.
- Add file-based snapshot validation logic for `snapshots validate --dir <DIR>` using the existing XML parser and fetch sidecar contract.
- Add deterministic `report diff --old <FILE> --new <FILE> [--format markdown] [--out <FILE>]` rendering over local snapshots with auto-resolved sidecars.
- Add or update tests and README documentation directly related to the new local snapshot inventory and report commands.
- Refresh this contract so PR3 scope, stop conditions, escalation triggers, and acceptance criteria are explicitly anchored to this work.
## Intentional amendments
- This PR intentionally replaces the prior governance-sync active contract with a feature-delivery contract for PR3.
- Historical governance-sync work remains evidence only; it is not active implementation scope.
- The fixed Graph metadata endpoint boundary and standard-library-first runtime remain durable carry-forward constraints.
- This PR adds the local filing-cabinet/report-printer layer only; it does not build a scheduler, service, or observability product surface.
## Forbidden scope
- Do not modify the Graph metadata fetch allowlist or permit arbitrary URLs.
- Do not add authentication, tenant access, secrets handling, or any privileged Microsoft 365 access path.
- Do not add persistence beyond existing local snapshot files and adjacent sidecars.
- Do not remove or weaken deterministic ordering guarantees in parser, diff, or output rendering.
- Do not change CI scope, add new toolchains, or introduce non-standard-library runtime packages.
- Do not change completed PR acceptance criteria except by preserving their durable invariants.
## Architectural constraints
- Keep `src/graph_schema_monitor/parser.py` as the local CSDL parsing primitive.
- Keep `src/graph_schema_monitor/diff.py` as the deterministic change engine reused by new reporting surfaces.
- Keep fetch sidecars adjacent to snapshot XML files and anchored to the existing allowlisted metadata fields.
- Keep CLI output deterministic and file-based.
- Keep new functionality composable over already-fetched local snapshots rather than adding new online behavior.
## Security constraints
- No secrets, credentials, tokens, tenant data, or private customer data may be introduced.
- Do not weaken the fixed Graph metadata network boundary.
- Treat CLI paths, local XML, and sidecar JSON as untrusted inputs and validate them before rendering reports.
- Do not introduce any capability to fetch non-Graph endpoints or follow redirects.
## Files expected to change
- `.github/aadlc/current-pr-contract.md`
- `README.md`
- `src/graph_schema_monitor/cli.py`
- `src/graph_schema_monitor/report.py`
- `src/graph_schema_monitor/snapshots.py`
- `tests/test_cli.py`
- `tests/test_report.py`
- `tests/test_snapshots.py`
The following files may be reviewed to preserve existing contracts and invariants:
- `src/graph_schema_monitor/diff.py`
- `src/graph_schema_monitor/fetcher.py`
- `src/graph_schema_monitor/parser.py`
- `.github/aadlc/memory.md`
- `.github/aadlc/trust-boundaries.md`
- `.github/aadlc/invariants.yml`
## Tests / validation
- Run `python -m pytest tests/`.
- Confirm existing `fetch`, `inspect`, and top-level `diff` tests still pass unchanged.
- Confirm new snapshot inventory and validation commands behave deterministically over local files.
- Confirm `report diff` renders deterministic markdown and writes to stdout or `--out` as requested.
- Confirm report generation only uses local snapshots plus auto-resolved adjacent sidecars and does not add new network behavior.
## Stop conditions
- A requested change would introduce a database, scheduler, daemon, web UI, or any persistent service layer.
- A requested change would require authentication, tenant access, arbitrary URL fetching, or any network boundary expansion.
- A requested change would break or replace existing `fetch`, `inspect`, or top-level `diff` behavior instead of extending the CLI alongside it.
- A requested change would require a new runtime dependency or non-file-based storage surface.
- The sidecar contract needed for local report rendering is ambiguous or would need to diverge from the existing fetch contract.
## Escalation triggers
- Need to change the sidecar schema, allowlisted fields, or fetch trust boundary.
- Need to support recursive inventory semantics beyond straightforward local file discovery and the intended behavior is unclear.
- Need to support report formats beyond markdown or reporting behavior that conflicts with current deterministic diff output.
- Need to alter durable invariants in `.github/aadlc/memory.md`, `.github/aadlc/trust-boundaries.md`, or `.github/aadlc/invariants.yml`.
- Need to expand scope into scheduling, persistence, UI, or any online correlation feature.
## Context reset notes
- Mark this contract complete after PR3 inventory and report commands are merged.
- Future PRs should create a fresh active contract before adding scheduler, UI, persistence, or broader reporting layers.
- Future substantial or boundary-sensitive tasks should use `.github/aadlc/plans/` rather than large UI prompts.
- Completed PR constraints should be treated as historical evidence unless promoted to durable invariants.
## PR3 acceptance criteria
- `python -m graph_schema_monitor snapshots list --dir <DIR>` inventories local snapshot files deterministically.
- `python -m graph_schema_monitor snapshots validate --dir <DIR>` validates local snapshot/sidecar pairs and exits non-zero on invalid inventory.
- `python -m graph_schema_monitor report diff --old <FILE> --new <FILE>` renders a deterministic markdown report over local snapshots using auto-resolved sidecars.
- `report diff` supports `--format markdown` with default markdown behavior and optional `--out` file writing, otherwise stdout.
- Existing `fetch`, `inspect`, and top-level `diff` behavior remains intact.
- No database, scheduler, web UI, changelog correlation, authentication, tenant access, new network behavior, or AI summarization is introduced.
