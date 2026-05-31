You are Claude Sonnet 4.6 acting as the implementation agent in Graham’s AADLCv2 workflow.

Repository:

https://github.com/goldjg/m365-graph-schema-monitor

This is PR9.

OPERATING MODE: Plan first.

First produce the implementation plan. Do not edit files until Graham explicitly replies with “approved”, “implement”, or “proceed”.

After approval, implement exactly the approved plan. Do not broaden scope.

────────────────────────────────────────
PR9 GOAL
────────────────────────────────────────

Add an end-to-end local evidence workflow command that bundles existing public-vs-authenticated Graph $metadata comparison outputs into a deterministic report directory.

PR9 builds on:

* PR1: offline CSDL/XML parser and deterministic diff foundation.
* PR2: public unauthenticated Graph $metadata fetch + sidecar.
* PR3: local snapshot inventory and deterministic reports.
* PR4: deterministic report filtering and summaries.
* PR5: local schema watchlists.
* PR6: version/content/semantic movement comparison.
* PR7: authenticated Graph $metadata fetch using externally supplied env-token.
* PR8: public-vs-authenticated local source comparison.

PR9 must not add new analysis semantics. It should orchestrate existing primitives and write a small deterministic evidence bundle.

It should answer:

Given a public snapshot and an authenticated snapshot, produce the local evidence bundle I would otherwise generate manually.

PR9 is local-first, deterministic, file-based, and standard-library-only.

No fetching.
No new network behaviour.
No token handling.
No authentication.
No tenant discovery.
No scheduler.
No database.
No web UI.
No changelog/docs correlation.
No AI summarisation.

────────────────────────────────────────
STRATEGIC CONTEXT
────────────────────────────────────────

The project now has a complete local evidence chain:

* fetch public metadata
* fetch authenticated metadata
* compare version/content/semantic movement
* compare public-vs-authenticated source provenance
* render deterministic reports
* evaluate local watchlists

PR9 makes the already-working manual chain repeatable by producing a local report bundle.

It is not a scheduler, not a database, not an observatory, and not a live acquisition workflow.

────────────────────────────────────────
HARD BOUNDARIES
────────────────────────────────────────

Allowed in PR9:

* Add a local workflow module, for example:
    * src/graph_schema_monitor/workflows.py
* Add a CLI command such as:
    * workflow compare-public-auth
* Consume existing local snapshot XML files and adjacent sidecars.
* Reuse existing functions:
    * build_source_comparison()
    * render_source_comparison_markdown()
    * render_source_comparison_json()
    * build_version_comparison()
    * render_version_comparison_markdown()
    * render_version_comparison_json()
    * build_summary_report()
    * optionally watchlist functions if --watchlist is supplied
* Write deterministic output files into an output directory.
* Write a deterministic manifest.json.
* Add tests with local fixtures only.
* Update README and AADLC artefacts.

Forbidden in PR9:

* No network calls.
* No fetch or fetch-auth execution.
* No MSAL.
* No device code flow.
* No browser login.
* No client secret support.
* No certificate credential support.
* No token acquisition.
* No token cache.
* No token persistence.
* No tenant discovery.
* No Graph SDK.
* No arbitrary URL fetching.
* No sovereign cloud support.
* No scheduler.
* No database.
* No web UI.
* No changelog/docs correlation.
* No AI summarisation.
* No new runtime dependencies.
* No parser expansion.
* No NavigationProperty diffing.
* No inherited-property flattening.
* No changes to existing report semantics unless a strict bug is found and Graham approves.

Python standard library only.

────────────────────────────────────────
STEP 0 — READ BEFORE PLANNING
────────────────────────────────────────

Before planning, read these files in full and record current-state observations:

.github/copilot-instructions.md
.github/aadlc/current-pr-contract.md
.github/aadlc/memory.md
.github/aadlc/trust-boundaries.md
.github/aadlc/invariants.yml
.github/aadlc/plans/plan-template.md
README.md

src/graph_schema_monitor/fetcher.py
src/graph_schema_monitor/snapshots.py
src/graph_schema_monitor/versioning.py
src/graph_schema_monitor/source_compare.py
src/graph_schema_monitor/report.py
src/graph_schema_monitor/report_filters.py
src/graph_schema_monitor/watchlists.py
src/graph_schema_monitor/cli.py
src/graph_schema_monitor/parser.py
src/graph_schema_monitor/diff.py

tests/test_fetcher.py
tests/test_snapshots.py
tests/test_versioning.py
tests/test_source_compare.py
tests/test_watchlists.py
tests/test_report.py
tests/test_cli.py
tests/fixtures/

Record especially:

* Existing version compare command shape and renderers.
* Existing version compare-sources command shape and renderers.
* Existing report summary behaviour.
* Existing watchlist loading/matching/rendering behaviour.
* Existing _write_output_file() or atomic file-writing helper.
* Current sidecar compatibility behaviour.
* Current invariants and trust boundaries around local-only workflows.
* Whether existing renderers include wall-clock timestamps. PR9 must not introduce new wall-clock timestamps into generated reports or manifest.

If any assumption in this prompt conflicts with current repo state, stop and report the conflict before planning implementation.

────────────────────────────────────────
PR9 DESIGN INTENT
────────────────────────────────────────

PR9 should add a small orchestration layer over existing primitives.

Default design preference:

* Add src/graph_schema_monitor/workflows.py.
* Do not modify source_compare.py, versioning.py, report.py, watchlists.py, fetcher.py, snapshots.py, parser.py, or diff.py.
* Add one CLI command under a new top-level workflow group.
* Keep workflow output deterministic and file-based.
* No fetching or token access.

The workflow should produce a directory like:

reports/beta-public-auth/
  source-comparison.json
  source-comparison.md
  version-comparison.json
  version-comparison.md
  summary.json
  summary.md
  manifest.json

If --watchlist is supplied, also produce:

  watchlist.json
  watchlist.md

The exact filenames should be stable and documented.

────────────────────────────────────────
PROPOSED CLI
────────────────────────────────────────

Add a new top-level workflow command with a compare-public-auth subcommand:

python -m graph_schema_monitor workflow compare-public-auth \
  --public <PUBLIC_XML> \
  --authenticated <AUTHENTICATED_XML> \
  --out-dir <DIR> \
  [--watchlist <WATCHLIST_JSON>] \
  [--allow-profile-mismatch] \
  [--overwrite]

Arguments:

* --public: required path to public/unauthenticated metadata snapshot XML.
* --authenticated: required path to authenticated metadata snapshot XML.
* --out-dir: required output directory for generated evidence bundle.
* --watchlist: optional local watchlist JSON path.
* --allow-profile-mismatch: optional flag passed to source comparison.
* --overwrite: optional flag.
    * If omitted and any planned output file already exists, fail before writing anything.
    * If supplied, overwrite existing planned output files atomically.

Existing commands must remain unchanged:

python -m graph_schema_monitor fetch ...
python -m graph_schema_monitor fetch-auth ...
python -m graph_schema_monitor inspect ...
python -m graph_schema_monitor diff ...
python -m graph_schema_monitor snapshots list ...
python -m graph_schema_monitor snapshots validate ...
python -m graph_schema_monitor report diff ...
python -m graph_schema_monitor report summary ...
python -m graph_schema_monitor watchlist check ...
python -m graph_schema_monitor version compare ...
python -m graph_schema_monitor version compare-sources ...

If Codex proposes a different CLI shape, it must justify the choice and preserve all existing commands.

────────────────────────────────────────
WORKFLOW OUTPUTS
────────────────────────────────────────

Required outputs without --watchlist:

1. source-comparison.json
    * Output from existing PR8 source comparison JSON renderer.
2. source-comparison.md
    * Output from existing PR8 source comparison Markdown renderer.
3. version-comparison.json
    * Output from existing PR6 version comparison JSON renderer.
4. version-comparison.md
    * Output from existing PR6 version comparison Markdown renderer.
5. summary.json
    * Output from existing PR4 summary report JSON renderer for public vs authenticated snapshots.
6. summary.md
    * Output from existing PR4 summary report Markdown renderer for public vs authenticated snapshots.
7. manifest.json
    * New PR9 manifest describing the workflow inputs and generated outputs.

Optional outputs with --watchlist:

8. watchlist.json
    * Existing PR5 watchlist JSON report for public vs authenticated snapshots and the supplied watchlist.
9. watchlist.md
    * Existing PR5 watchlist Markdown report for public vs authenticated snapshots and the supplied watchlist.

Do not include individual full diff report outputs in PR9 unless Codex justifies it. The summary/source/version/watchlist outputs are the intended bundle.

────────────────────────────────────────
MANIFEST DESIGN
────────────────────────────────────────

Add a deterministic manifest.json.

Suggested field order:

MANIFEST_FIELDS = (
    "manifest_type",
    "workflow",
    "public_snapshot",
    "authenticated_snapshot",
    "watchlist",
    "allow_profile_mismatch",
    "outputs",
)

Suggested JSON:

{
  "manifest_type": "workflow_bundle",
  "workflow": "compare_public_authenticated",
  "public_snapshot": "snapshots/graph-beta-public.xml",
  "authenticated_snapshot": "snapshots/graph-beta-auth.xml",
  "watchlist": "watchlists/identity-critical.json",
  "allow_profile_mismatch": false,
  "outputs": {
    "source_comparison_json": "source-comparison.json",
    "source_comparison_markdown": "source-comparison.md",
    "version_comparison_json": "version-comparison.json",
    "version_comparison_markdown": "version-comparison.md",
    "summary_json": "summary.json",
    "summary_markdown": "summary.md",
    "watchlist_json": "watchlist.json",
    "watchlist_markdown": "watchlist.md"
  }
}

If no watchlist is supplied:

* watchlist: null
* omit watchlist output keys from outputs

Rules:

* No wall-clock timestamps.
* No token/env data.
* No absolute path rewriting unless the input paths were absolute.
* Use json.dumps(..., indent=2) without sort_keys.
* Field order is part of the contract.
* Output paths in outputs should be relative filenames within the bundle directory, not absolute paths.

────────────────────────────────────────
PROPOSED DATA MODEL
────────────────────────────────────────

Add a frozen dataclass, suggested:

@dataclass(frozen=True)
class WorkflowBundle:
    workflow: str
    public_snapshot: Path
    authenticated_snapshot: Path
    watchlist: Path | None
    allow_profile_mismatch: bool
    output_dir: Path
    outputs: dict[str, Path]

Functions, suggested:

def build_compare_public_auth_bundle(
    public_snapshot_path: str | Path,
    authenticated_snapshot_path: str | Path,
    out_dir: str | Path,
    *,
    watchlist_path: str | Path | None = None,
    allow_profile_mismatch: bool = False,
    overwrite: bool = False,
) -> WorkflowBundle:
    ...
def render_manifest_json(bundle: WorkflowBundle) -> str:
    ...

Codex may propose different names, but must keep the design small and testable.

────────────────────────────────────────
IMPLEMENTATION REQUIREMENTS
────────────────────────────────────────

build_compare_public_auth_bundle() must:

1. Resolve planned output paths.
2. Validate output directory:
    * If out_dir does not exist, create it.
    * If out_dir exists but is not a directory, fail with SnapshotValidationError.
    * Do not create parent directories recursively unless Codex justifies it.
    * Default preference: create only the final out_dir if its parent exists.
3. Validate overwrite behaviour before doing expensive work:
    * Compute the full list of planned output files.
    * If any planned output exists and overwrite=False, raise SnapshotValidationError before writing anything.
    * If overwrite=True, overwrite planned files atomically.
4. Build all report content in memory first:
    * Source comparison Markdown/JSON.
    * Version comparison Markdown/JSON.
    * Summary Markdown/JSON.
    * Optional watchlist Markdown/JSON.
    * Manifest JSON.
5. Only after all content has been generated successfully, write files.
6. Use an atomic write helper:
    * Prefer reusing cli._write_output_file() if acceptable.
    * If importing from cli.py would create undesirable coupling, add a small private _write_text_file_atomic() helper in workflows.py.
    * Do not duplicate fragile partial-write behaviour.
    * If any write fails, raise SnapshotValidationError.
7. Return a WorkflowBundle with generated output paths.

Implementation must not:

* call fetch_snapshot()
* call fetch_authenticated_snapshot()
* read environment variables
* open network sockets
* mutate input snapshots or sidecars
* emit wall-clock timestamps

────────────────────────────────────────
WATCHLIST INTEGRATION
────────────────────────────────────────

If --watchlist is supplied:

* Load the watchlist using existing load_watchlist().
* Load public/auth snapshot bundles using existing load_snapshot_bundle().
* Compute changes using existing diff_snapshots().
* Match changes using existing match_watchlist().
* Render using existing:
    * render_watchlist_markdown_report()
    * render_watchlist_json_report()

Do not reimplement watchlist matching or rendering.

If no --watchlist is supplied, do not write watchlist outputs and set manifest watchlist to null.

Watchlist path is local input only. No network. No expansion into watchlist packs in PR9.

────────────────────────────────────────
CONTRACT ASSERTIONS
────────────────────────────────────────

The plan must include 5 contract assertions that tests directly assert.

At minimum:

CA-1 — Workflow output set

* Without --watchlist, the workflow writes exactly:
    * source-comparison.json
    * source-comparison.md
    * version-comparison.json
    * version-comparison.md
    * summary.json
    * summary.md
    * manifest.json
* With --watchlist, it also writes:
    * watchlist.json
    * watchlist.md

CA-2 — Manifest schema stability

* manifest.json has exactly the approved top-level fields in stable order.
* Output paths in outputs are relative filenames, not absolute paths.
* watchlist is null when no watchlist is supplied.

CA-3 — Atomic/no-partial-write behaviour

* If any planned output already exists and --overwrite is not supplied, the command fails before writing any output files.
* If report generation fails before writing, no partial bundle files are left behind.

CA-4 — Existing primitive reuse

* Source comparison output matches render_source_comparison_json(build_source_comparison(...)).
* Version comparison output matches render_version_comparison_json(build_version_comparison(...)).
* Summary output matches build_summary_report(..., output_format="json").
* Watchlist output, when supplied, matches existing watchlist renderer output.

CA-5 — Local-only/no-auth behaviour

* Workflow command performs no network calls.
* Workflow command does not read tokens or environment variables.
* Workflow command does not call fetch or fetch-auth.

────────────────────────────────────────
TEST PLAN REQUIREMENTS
────────────────────────────────────────

Add or update tests for:

Workflow output set:

* bundle without watchlist writes exactly 7 files.
* bundle with watchlist writes exactly 9 files.
* output filenames are stable.
* output directory is created when parent exists.
* output fails if out-dir parent does not exist.
* output fails if out-dir path exists as a file.

Manifest:

* manifest has exact approved field order.
* manifest outputs values are relative filenames.
* manifest watchlist is null when omitted.
* manifest includes watchlist path when supplied.
* manifest output keys match generated files.

Overwrite/no partial writes:

* existing planned output without --overwrite fails before writing anything.
* existing planned output with --overwrite succeeds.
* simulated render failure before write leaves output directory empty or without planned outputs.
* simulated write failure leaves no temp files behind if practical.

Primitive reuse:

* generated source-comparison.json equals direct renderer output.
* generated version-comparison.json equals direct renderer output.
* generated summary.json equals direct build_summary_report output.
* generated watchlist.json equals direct watchlist renderer output when watchlist supplied.

CLI:

* workflow compare-public-auth success without watchlist.
* workflow compare-public-auth success with watchlist.
* workflow compare-public-auth --overwrite works.
* missing required args fail through argparse.
* profile mismatch failure propagates exit 2.
* --allow-profile-mismatch succeeds and generated source comparison contains warning.

Local-only:

* monkeypatch socket/socket.create_connection to fail; workflow still succeeds using local fixtures.
* monkeypatch os.environ.get to raise; workflow still succeeds.
* monkeypatch fetcher.fetch_snapshot and fetcher.fetch_authenticated_snapshot to raise if called; workflow still succeeds.

Regression:

* Existing PR1–PR8 tests still pass unchanged.

────────────────────────────────────────
README UPDATE
────────────────────────────────────────

Add a “Local evidence workflow bundle” section.

Document:

* It consumes already-fetched public and authenticated snapshots.
* It does not fetch anything.
* It does not read or use tokens.
* Example:

python -m graph_schema_monitor workflow compare-public-auth \
  --public snapshots/graph-beta-public.xml \
  --authenticated snapshots/graph-beta-auth.xml \
  --out-dir reports/beta-public-auth

* Example with watchlist:

python -m graph_schema_monitor workflow compare-public-auth \
  --public snapshots/graph-beta-public.xml \
  --authenticated snapshots/graph-beta-auth.xml \
  --watchlist examples/watchlists/identity-critical.json \
  --out-dir reports/beta-public-auth \
  --overwrite

* List generated files.
* Explain manifest.
* Explain no scheduler/database/web UI/fetching.

────────────────────────────────────────
AADLC UPDATES
────────────────────────────────────────

Update:

* .github/aadlc/current-pr-contract.md
* .github/aadlc/memory.md
* .github/aadlc/invariants.yml only if a new durable invariant is justified
* .github/aadlc/trust-boundaries.md only if a new trust boundary is justified
* README.md

Expected trust-boundary decision:

Probably no new trust boundary is needed.

PR9 consumes existing local snapshots, sidecars, and optional local watchlist JSON via existing validation surfaces. It creates local report files only.

Expected invariant decision:

Candidate invariant:

- id: workflow-bundles-local-only
  name: Workflow bundles are local-only
  rule: >
    Workflow bundle generation must use only local snapshots, adjacent validated sidecars,
    optional local watchlists, and existing local renderers. It must not introduce fetching,
    network calls, authentication, token handling, tenant discovery, external correlation,
    scheduler behaviour, or database persistence.
  severity: high

Codex should propose adding this only if consistent with existing invariant style and not redundant.

Current PR contract must be replaced with PR9 active contract.

Preserve prior durable state:

* network-boundary-fixed / graph-metadata-network-boundary-fixed
* auth-token-not-persisted
* watchlists-local-only
* version-comparison-local-only
* source-comparison-local-only

────────────────────────────────────────
STOP CONDITIONS
────────────────────────────────────────

Stop and ask Graham before proceeding if:

* Implementing workflow bundle requires changing fetcher.py.
* Implementing workflow bundle requires changing source_compare.py.
* Implementing workflow bundle requires changing versioning.py.
* Implementing workflow bundle requires changing report.py or watchlists.py.
* Any network call becomes necessary.
* Any token/env access becomes necessary.
* Any live fetching is proposed.
* Existing report/source/version/watchlist behaviour would need to change.
* Atomic/no-partial-write behaviour cannot be implemented simply.
* Existing tests would need weakening.
* Correction budget is exceeded.

────────────────────────────────────────
ESCALATION TRIGGERS
────────────────────────────────────────

Ask Graham before proceeding if proposing:

* Live public/auth fetching.
* Token handling.
* Tenant ID capture.
* Watchlist packs.
* HTML output.
* New report formats.
* Scheduler or recurring workflow.
* Database or persistent run history.
* New dependencies.
* Changes to parser/diff/fetch/source/version/report/watchlist semantics.

────────────────────────────────────────
ACCEPTANCE CRITERIA
────────────────────────────────────────

The PR is ready when:

* python -m pytest tests/ passes.
* Existing PR1–PR8 commands and tests remain unchanged.
* workflow compare-public-auth writes the required report bundle.
* Bundle without watchlist contains exactly 7 expected files.
* Bundle with watchlist contains exactly 9 expected files.
* manifest.json has approved stable fields and relative output filenames.
* Existing planned outputs cause failure unless --overwrite is supplied.
* No partial planned outputs are left after pre-write failures.
* Generated reports match the existing direct renderers.
* No network calls are introduced.
* No token/env access is introduced.
* No new runtime dependencies.
* README documents the workflow bundle.
* AADLC artefacts reflect PR9 scope without removing prior durable state.

────────────────────────────────────────
FINAL RESPONSE FORMAT FOR PLAN
────────────────────────────────────────

When producing the plan, include these headings:

Summary

Current-state observations

Proposed file changes

PR contract updates

Workflow design

Manifest design

CLI design

Atomic write / no-partial-output design

Watchlist integration

Security and local-only model

Test plan

README updates

AADLC updates

Stop conditions

Escalation triggers

Acceptance criteria

Risks

Changes

No code changes proposed (Plan-only mode).

Tests run / not run

Not run (Plan-only mode).

After Graham approves the plan, implement exactly that plan.
