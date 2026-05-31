You are Claude Sonnet 4.6 acting as the implementation agent in Graham’s AADLCv2 workflow.

Repository:

https://github.com/goldjg/m365-graph-schema-monitor

This is PR8.

OPERATING MODE: Plan first.

First produce the implementation plan. Do not edit files until Graham explicitly replies with “approved”, “implement”, or “proceed”.

After approval, implement exactly the approved plan. Do not broaden scope.

────────────────────────────────────────
PR8 GOAL
────────────────────────────────────────

Add a first-class public-vs-authenticated Graph $metadata comparison command.

PR8 builds on:

* PR1: offline CSDL/XML parser and deterministic diff foundation.
* PR2: public unauthenticated Graph $metadata fetch + sidecar.
* PR3: local snapshot inventory and deterministic reports.
* PR4: deterministic report filtering and summaries.
* PR5: local schema watchlists.
* PR6: version/content/semantic movement comparison.
* PR7: authenticated Graph $metadata fetch using an externally supplied env-token, with authenticated provenance sidecar fields.

PR8 does not add new acquisition. It compares existing local snapshot files.

It should answer:

Does the public Graph $metadata snapshot match the authenticated Graph $metadata snapshot for the same profile?

PR8 must distinguish:

* schema version movement
* raw content movement
* semantic schema movement
* provenance/source-kind mismatch

It should make the manual workflow Graham just tested into a supported command.

────────────────────────────────────────
STRATEGIC CONTEXT
────────────────────────────────────────

The project is moving toward evidence-based Graph schema monitoring:

* public-observed metadata
* authenticated-observed metadata
* version movement
* content movement
* semantic movement
* watched movement

PR7 proved authenticated acquisition works.

PR8 makes the public-vs-authenticated comparison explicit and repeatable.

This is still local-first, deterministic, file-based, and standard-library-only.

No new network behaviour.
No new authentication.
No token handling.
No token acquisition.
No tenant discovery.
No scheduler.
No database.
No web UI.
No changelog/docs correlation.
No AI summarisation.

────────────────────────────────────────
HARD BOUNDARIES
────────────────────────────────────────

Allowed in PR8:

* Add a local comparison command that consumes:
    * one public metadata snapshot XML
    * one authenticated metadata snapshot XML
* Load both through existing snapshot/sidecar validation surfaces.
* Reuse PR6 version/content/semantic comparison logic.
* Validate or warn on provenance expectations:
    * public snapshot should be public/unauthenticated provenance
    * authenticated snapshot should have authenticated provenance if available
    * profiles should match unless explicitly allowed otherwise
* Render deterministic Markdown and JSON reports.
* Add tests with local fixtures only.
* Update README and AADLC artefacts.

Forbidden in PR8:

* No new network calls.
* No fetch or fetch-auth changes unless a strict compatibility bug is found and Graham approves.
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
* No public-vs-authenticated live fetching in this PR.

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
src/graph_schema_monitor/cli.py
src/graph_schema_monitor/parser.py
src/graph_schema_monitor/diff.py
src/graph_schema_monitor/report.py
src/graph_schema_monitor/report_filters.py
src/graph_schema_monitor/watchlists.py

tests/test_fetcher.py
tests/test_snapshots.py
tests/test_versioning.py
tests/test_cli.py
tests/test_report.py
tests/test_watchlists.py
tests/fixtures/

Record especially:

* Current PR7 authenticated sidecar extra fields.
* Whether authenticated sidecar extra fields are ignored with warnings by snapshot validation.
* Existing SnapshotSidecar model and whether it exposes extra sidecar fields.
* Existing load_snapshot_bundle() behaviour.
* Existing build_version_comparison() API and VersionComparison dataclass.
* Existing version comparison JSON/Markdown field order.
* Current CLI nesting patterns.
* Current invariants and trust boundaries relating to local-only comparison and authenticated token handling.
* Whether sidecar extra fields can be loaded from raw JSON without weakening central validation.

If any assumption in this prompt conflicts with current repo state, stop and report the conflict before planning implementation.

────────────────────────────────────────
PR8 DESIGN INTENT
────────────────────────────────────────

PR8 should preferably add a small module that composes existing primitives instead of changing them.

Default design preference:

* Keep versioning.py unchanged if possible.
* Add a new module, for example:
    * src/graph_schema_monitor/source_compare.py
* This module should:
    * load two local snapshot bundles
    * inspect adjacent sidecar JSON provenance
    * call build_version_comparison(public_snapshot, authenticated_snapshot)
    * classify public-vs-authenticated source relationship
    * render Markdown/JSON reports

Do not reimplement parsing or diffing.

Do not change public fetch or authenticated fetch behaviour.

────────────────────────────────────────
PROPOSED CLI
────────────────────────────────────────

Add a new subcommand under the existing version group:

python -m graph_schema_monitor version compare-sources \
  --public <PUBLIC_XML> \
  --authenticated <AUTHENTICATED_XML> \
  [--format {markdown,json}] \
  [--out <FILE>] \
  [--allow-profile-mismatch]

Arguments:

* --public: required path to public/unauthenticated metadata snapshot XML
* --authenticated: required path to authenticated metadata snapshot XML
* --format: optional, markdown default, json supported
* --out: optional output path; stdout if omitted
* --allow-profile-mismatch: optional flag
    * default false
    * if false, profile mismatch is an error
    * if true, profile mismatch is allowed but reported

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

If Codex proposes a different CLI shape, it must justify the choice and preserve all existing commands.

────────────────────────────────────────
SOURCE / PROVENANCE MODEL
────────────────────────────────────────

PR7 authenticated sidecars may include extra fields:

* source_kind: "authenticated_graph_metadata"
* auth_mode: "env_token"
* tenant_label: string or null

Public sidecars from older PR2 fetches may not have source_kind.

PR8 must not require older public sidecars to be refetched.

Expected provenance interpretation:

Public snapshot:

* If no source_kind field exists:
    * treat as "public_graph_metadata" for compatibility.
* If source_kind == "public_graph_metadata":
    * treat as public.
* If source_kind == "authenticated_graph_metadata":
    * error unless Codex proposes warning-only behaviour and justifies it.
* Other source_kind values:
    * error.

Authenticated snapshot:

* Must have source_kind == "authenticated_graph_metadata".
* Must have auth_mode == "env_token" for PR8.
* tenant_label may be string or null.
* Missing authenticated provenance should be an error for compare-sources.
    * Reason: this command is specifically about public-vs-authenticated evidence.

Profile handling:

* Both snapshots should normally have the same profile.
* If profiles differ and --allow-profile-mismatch is false:
    * fail with exit code 2.
* If profiles differ and --allow-profile-mismatch is true:
    * allow report generation and include a warning in output.

Do not infer tenant identity.

Do not interpret tenant_label as authoritative identity.

Do not require or store tenant ID.

────────────────────────────────────────
COMPARISON CLASSIFICATION
────────────────────────────────────────

PR8 should reuse the PR6 classification from VersionComparison for:

* schema_version_changed
* sha256_changed
* semantic_changes_present
* classification

PR8 should add public-vs-authenticated source classification.

Suggested source comparison states:

public_auth_same_version_same_content_same_semantics
public_auth_same_version_same_content_changed_semantics_same
public_auth_same_version_same_content_changed_semantics_changed
public_auth_version_changed_content_same_semantics_same
public_auth_version_changed_content_same_semantics_changed
public_auth_version_changed_content_changed_semantics_same
public_auth_version_changed_content_changed_semantics_changed

Codex may propose a simpler mapping by reusing the PR6 classification string plus comparison_kind = "public_vs_authenticated". If so, justify it.

Default preference:

* Do not create a second redundant eight-state classification if PR6’s classification already carries the version/content/semantic signal.
* Instead, expose:
    * comparison_kind: "public_vs_authenticated"
    * version_classification: <PR6 classification string>
    * source_validation_status: "valid" or "profile_mismatch_allowed"
    * warnings: list[str]

This avoids duplicating classification logic.

────────────────────────────────────────
PROPOSED DATA MODEL
────────────────────────────────────────

Add a frozen dataclass, suggested:

@dataclass(frozen=True)
class SourceComparison:
    comparison_kind: str
    public_snapshot: Path
    authenticated_snapshot: Path
    public_profile: str | None
    authenticated_profile: str | None
    public_source_kind: str
    authenticated_source_kind: str
    authenticated_auth_mode: str | None
    authenticated_tenant_label: str | None
    profile_mismatch: bool
    warnings: tuple[str, ...]
    version_comparison: VersionComparison

Functions, suggested:

def build_source_comparison(
    public_snapshot_path: str | Path,
    authenticated_snapshot_path: str | Path,
    *,
    allow_profile_mismatch: bool = False,
) -> SourceComparison:
    ...
def render_source_comparison_markdown(comparison: SourceComparison) -> str:
    ...
def render_source_comparison_json(comparison: SourceComparison) -> str:
    ...

Codex may propose different names, but must keep the design small and testable.

────────────────────────────────────────
RAW SIDECAR EXTRA FIELD LOADING
────────────────────────────────────────

Current SnapshotSidecar may not expose extra fields.

If authenticated provenance fields are not exposed by SnapshotSidecar, PR8 may read adjacent sidecar JSON directly to inspect:

* source_kind
* auth_mode
* tenant_label

This is allowed only for provenance interpretation.

Rules:

* Use json.loads() or json.load().
* Do not bypass existing load_snapshot_bundle() validation.
* First call existing load_snapshot_bundle() for both snapshots to validate XML, required sidecar fields, profile/source_url/sha256.
* Then read raw sidecar JSON for optional provenance extras.
* Do not execute or eval anything.
* Do not alter sidecar files.
* Do not weaken snapshot validation.

If Codex proposes changing SnapshotSidecar to expose extra fields, it must justify why that is necessary and prove no existing behaviour breaks. Default preference: do not change snapshots.py in PR8.

────────────────────────────────────────
MARKDOWN OUTPUT DESIGN
────────────────────────────────────────

Required Markdown structure:

# Graph Schema Source Comparison
## Sources
- Comparison kind: public_vs_authenticated
- Public snapshot: <path>
- Authenticated snapshot: <path>
- Public source kind: <public_graph_metadata>
- Authenticated source kind: <authenticated_graph_metadata>
- Auth mode: <env_token>
- Tenant label: <value or "none">
## Profiles
- Public profile: <value>
- Authenticated profile: <value>
- Profile mismatch: <true|false>
## Version and Content
- Public x-ms-schemaVersion: <value>
- Authenticated x-ms-schemaVersion: <value>
- Schema version changed: <true|false>
- Public sha256: <value>
- Authenticated sha256: <value>
- SHA-256 changed: <true|false>
## Semantic Diff
- Semantic change count: <N>
- Semantic changes present: <true|false>
## Classification
- Version classification: `<PR6 classification>`
## Warnings
None.

If warnings exist, list them as bullets.

No wall-clock timestamps.

Do not list individual schema changes in PR8. Existing report diff, report summary, and watchlist check already provide that.

────────────────────────────────────────
JSON OUTPUT DESIGN
────────────────────────────────────────

Define an explicit field-order tuple, for example:

JSON_SOURCE_COMPARISON_FIELDS = (
    "report_type",
    "comparison_kind",
    "public_snapshot",
    "authenticated_snapshot",
    "public_profile",
    "authenticated_profile",
    "public_source_kind",
    "authenticated_source_kind",
    "authenticated_auth_mode",
    "authenticated_tenant_label",
    "profile_mismatch",
    "warnings",
    "public_x_ms_schema_version",
    "authenticated_x_ms_schema_version",
    "schema_version_changed",
    "public_sha256",
    "authenticated_sha256",
    "sha256_changed",
    "semantic_change_count",
    "semantic_changes_present",
    "version_classification",
)

JSON report:

{
  "report_type": "source_comparison",
  "comparison_kind": "public_vs_authenticated",
  "public_snapshot": "...",
  "authenticated_snapshot": "...",
  "public_profile": "beta",
  "authenticated_profile": "beta",
  "public_source_kind": "public_graph_metadata",
  "authenticated_source_kind": "authenticated_graph_metadata",
  "authenticated_auth_mode": "env_token",
  "authenticated_tenant_label": "lab",
  "profile_mismatch": false,
  "warnings": [],
  "public_x_ms_schema_version": "1.4.592",
  "authenticated_x_ms_schema_version": "1.4.592",
  "schema_version_changed": false,
  "public_sha256": "...",
  "authenticated_sha256": "...",
  "sha256_changed": false,
  "semantic_change_count": 0,
  "semantic_changes_present": false,
  "version_classification": "version_same_content_same_semantics_same"
}

Use json.dumps(..., indent=2) without sort_keys.

Do not include token data, token env var names, raw headers, request metadata, tenant IDs, user IDs, app IDs, or claims.

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

PR8 consumes existing local XML snapshots and adjacent sidecar JSON via existing validation surfaces. It reads sidecar extra provenance fields from local JSON, but this is still within the local sidecar input surface introduced by PR7.

If Codex thinks a new boundary is needed, justify it.

Expected invariant decision:

Candidate invariant:

- id: source-comparison-local-only
  name: Source comparison is local-only
  rule: >
    Public-vs-authenticated source comparison must use only local snapshots,
    adjacent validated sidecars, and existing version comparison output. It
    must not introduce network calls, authentication, token handling, tenant
    discovery, or external correlation.
  severity: high

Codex should propose adding this only if consistent with existing invariant style and not redundant.

Current PR contract must be replaced with PR8 active contract.

Preserve prior durable state:

* network-boundary-fixed / graph-metadata-network-boundary-fixed
* auth-token-not-persisted
* watchlists-local-only
* version-comparison-local-only

────────────────────────────────────────
CONTRACT ASSERTIONS
────────────────────────────────────────

The plan must include 5 contract assertions that tests directly assert.

At minimum:

CA-1 — Source provenance validation

* Public side accepts missing source_kind as public_graph_metadata.
* Public side rejects source_kind == authenticated_graph_metadata.
* Authenticated side requires source_kind == authenticated_graph_metadata.
* Authenticated side requires auth_mode == env_token.

CA-2 — Profile mismatch behaviour

* Profile mismatch fails with exit code 2 by default.
* Profile mismatch succeeds with --allow-profile-mismatch and emits a warning.

CA-3 — Version comparison reuse

* Source comparison reuses PR6 version comparison results.
* JSON output values for schema_version_changed, sha256_changed, semantic_change_count, semantic_changes_present, and version_classification match build_version_comparison(public, authenticated).

CA-4 — JSON schema stability

* version compare-sources --format json produces exactly the approved top-level fields in stable order.

CA-5 — Local-only/no-auth behaviour

* compare-sources performs no network calls.
* It does not read tokens or environment variables.
* It does not call fetch or fetch-auth.

────────────────────────────────────────
TEST PLAN REQUIREMENTS
────────────────────────────────────────

Add or update tests for:

Source provenance:

* public side with no source_kind accepted as public.
* public side with source_kind == public_graph_metadata accepted.
* public side with source_kind == authenticated_graph_metadata rejected.
* public side with unknown source_kind rejected.
* authenticated side with source_kind == authenticated_graph_metadata accepted.
* authenticated side missing source_kind rejected.
* authenticated side with source_kind == public_graph_metadata rejected.
* authenticated side with missing auth_mode rejected.
* authenticated side with auth_mode != env_token rejected.
* authenticated tenant_label string and null both accepted.

Profile handling:

* matching profiles succeeds.
* mismatched profiles fail by default.
* mismatched profiles succeed with allow_profile_mismatch=True.
* mismatched profiles with allow flag include warning.

Version comparison reuse:

* same public/auth snapshots produce same version classification as PR6.
* public/auth snapshots with different content produce semantic change count matching build_version_comparison().

JSON/Markdown:

* Markdown report has required sections.
* Markdown no-warning case prints None. under warnings.
* Markdown warning case lists warning bullet.
* JSON report has exact approved top-level fields.
* JSON field order is stable.
* JSON contains no token/env/header fields.

CLI:

* version compare-sources Markdown output.
* version compare-sources --format json.
* version compare-sources --out.
* default profile mismatch exits 2.
* --allow-profile-mismatch exits 0 with warning.
* invalid public provenance exits 2.
* invalid authenticated provenance exits 2.

Local-only:

* monkeypatch socket/socket.create_connection to fail; command still succeeds using local fixtures.
* monkeypatch os.environ.get to raise; command still succeeds.
* monkeypatch fetcher.fetch_snapshot and fetcher.fetch_authenticated_snapshot to raise if called; command still succeeds.

Regression:

* Existing PR1–PR7 tests still pass unchanged.

────────────────────────────────────────
IMPLEMENTATION CONSTRAINTS
────────────────────────────────────────

Prefer minimal implementation.

Likely file changes:

* src/graph_schema_monitor/source_compare.py
* src/graph_schema_monitor/cli.py
* tests/test_source_compare.py
* maybe tests/test_cli.py
* .github/aadlc/current-pr-contract.md
* .github/aadlc/memory.md
* maybe .github/aadlc/invariants.yml
* maybe .github/aadlc/trust-boundaries.md
* README.md

Files that should not change unless strictly necessary:

* fetcher.py
* snapshots.py
* versioning.py
* parser.py
* diff.py
* report.py
* report_filters.py
* watchlists.py
* existing fixtures, unless adding new fixtures only

Do not add new dependencies.

Do not broaden parser/diff/report/watchlist/fetch semantics.

────────────────────────────────────────
README UPDATE
────────────────────────────────────────

Add a “Public vs authenticated metadata comparison” section.

Document:

* It compares two already-fetched local XML snapshots.
* It does not fetch anything.
* It does not read or use tokens.
* Example:

python -m graph_schema_monitor version compare-sources \
  --public snapshots/2026-05-31/graph-beta-public.xml \
  --authenticated snapshots/lab/graph-beta-auth.xml \
  --format json

* Explain expected sidecar provenance:
    * public side may omit source_kind
    * authenticated side should have source_kind=authenticated_graph_metadata
    * authenticated side should have auth_mode=env_token
* Explain --allow-profile-mismatch.
* Show interpretation:
    * same version/content/semantics means public and authenticated metadata matched at capture time
    * same version but different content means raw payload difference
    * same version/content changed/semantic changed means meaningful schema difference

Do not document live fetching in PR8.

────────────────────────────────────────
STOP CONDITIONS
────────────────────────────────────────

Stop and ask Graham before proceeding if:

* Implementing source comparison requires changing fetcher.py.
* Implementing source comparison requires changing snapshots.py or SnapshotSidecar.
* Implementing source comparison requires changing versioning.py.
* Existing sidecar extra-field warning behaviour blocks implementation.
* Token access, token env vars, or auth handling becomes necessary.
* Any network call becomes necessary.
* Public-vs-authenticated comparison semantics are ambiguous enough to produce incompatible outputs.
* Existing public/auth fetch behaviour would need to change.
* Existing version comparison behaviour would need to change.
* Tests would need live network access.
* Correction budget is exceeded.

────────────────────────────────────────
ESCALATION TRIGGERS
────────────────────────────────────────

Ask Graham before proceeding if proposing:

* Live public/auth fetching.
* Source comparison inside version compare instead of separate version compare-sources.
* Token handling.
* Tenant ID capture.
* Tenant label requirements beyond reading existing sidecar value.
* Source labels beyond existing PR7 provenance fields.
* Multiple clouds.
* New dependencies.
* New report formats.
* Changes to parser/diff/fetch/version/watchlist semantics.

────────────────────────────────────────
ACCEPTANCE CRITERIA
────────────────────────────────────────

The PR is ready when:

* python -m pytest tests/ passes.
* Existing PR1–PR7 commands and tests remain unchanged.
* version compare-sources compares two local snapshots only.
* Public side missing source_kind is accepted as legacy public metadata.
* Authenticated side requires source_kind=authenticated_graph_metadata.
* Authenticated side requires auth_mode=env_token.
* Profile mismatch fails by default.
* Profile mismatch can be allowed with --allow-profile-mismatch and produces warning output.
* JSON output has approved stable top-level fields.
* Markdown output has required sections.
* Source comparison reuses PR6 version comparison output.
* No network calls are introduced.
* No token/env access is introduced.
* No new runtime dependencies.
* README documents the source comparison workflow.
* AADLC artefacts reflect PR8 scope without removing prior durable state.

────────────────────────────────────────
FINAL RESPONSE FORMAT FOR PLAN
────────────────────────────────────────

When producing the plan, include these headings:

Summary

Current-state observations

Proposed file changes

PR contract updates

Provenance model

Source comparison design

CLI design

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
