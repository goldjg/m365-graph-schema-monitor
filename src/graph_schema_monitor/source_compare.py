from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .snapshots import SnapshotValidationError, load_snapshot_bundle, sidecar_path_for_snapshot
from .versioning import VersionComparison, build_version_comparison


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

_VALID_PUBLIC_SOURCE_KINDS = ("public_graph_metadata",)
_VALID_AUTH_SOURCE_KIND = "authenticated_graph_metadata"
_VALID_AUTH_MODE = "env_token"


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


def build_source_comparison(
    public_snapshot_path: str | Path,
    authenticated_snapshot_path: str | Path,
    *,
    allow_profile_mismatch: bool = False,
) -> SourceComparison:
    """
    Load two local snapshot bundles, validate provenance, compare versions
    and semantics, and return a frozen SourceComparison. Raises
    SnapshotValidationError for invalid provenance or profile mismatch (when
    not allowed). No network access; no token or environment variable access.
    """
    public_path = Path(public_snapshot_path)
    auth_path = Path(authenticated_snapshot_path)

    # Validate both bundles via existing surface (XML parse + sidecar required fields + sha256)
    public_bundle = load_snapshot_bundle(public_path)
    auth_bundle = load_snapshot_bundle(auth_path)

    assert public_bundle.sidecar is not None
    assert auth_bundle.sidecar is not None

    # Read raw sidecar JSON for provenance extra fields
    public_raw = _read_raw_sidecar(public_path)
    auth_raw = _read_raw_sidecar(auth_path)

    # Validate public provenance
    public_source_kind = _validate_public_provenance(public_raw, public_path)

    # Validate authenticated provenance
    auth_source_kind, auth_mode, tenant_label = _validate_auth_provenance(auth_raw, auth_path)

    # Profile handling
    public_profile = public_bundle.sidecar.profile
    auth_profile = auth_bundle.sidecar.profile
    profile_mismatch = public_profile != auth_profile
    warnings: list[str] = []
    if profile_mismatch:
        if not allow_profile_mismatch:
            raise SnapshotValidationError(
                f"profile mismatch: public snapshot profile {public_profile!r} does not match "
                f"authenticated snapshot profile {auth_profile!r}. "
                f"Use --allow-profile-mismatch to override."
            )
        warnings.append(
            f"profile mismatch allowed: public profile {public_profile!r} vs "
            f"authenticated profile {auth_profile!r}"
        )

    # Reuse PR6 version comparison
    version_comparison = build_version_comparison(public_path, auth_path)

    return SourceComparison(
        comparison_kind="public_vs_authenticated",
        public_snapshot=public_path,
        authenticated_snapshot=auth_path,
        public_profile=public_profile,
        authenticated_profile=auth_profile,
        public_source_kind=public_source_kind,
        authenticated_source_kind=auth_source_kind,
        authenticated_auth_mode=auth_mode,
        authenticated_tenant_label=tenant_label,
        profile_mismatch=profile_mismatch,
        warnings=tuple(warnings),
        version_comparison=version_comparison,
    )


def render_source_comparison_markdown(comparison: SourceComparison) -> str:
    """Return deterministic Markdown string. No I/O."""
    vc = comparison.version_comparison
    tenant = comparison.authenticated_tenant_label if comparison.authenticated_tenant_label is not None else "none"
    lines = [
        "# Graph Schema Source Comparison",
        "",
        "## Sources",
        "",
        f"- Comparison kind: {comparison.comparison_kind}",
        f"- Public snapshot: {comparison.public_snapshot}",
        f"- Authenticated snapshot: {comparison.authenticated_snapshot}",
        f"- Public source kind: {comparison.public_source_kind}",
        f"- Authenticated source kind: {comparison.authenticated_source_kind}",
        f"- Auth mode: {comparison.authenticated_auth_mode}",
        f"- Tenant label: {tenant}",
        "",
        "## Profiles",
        "",
        f"- Public profile: {comparison.public_profile}",
        f"- Authenticated profile: {comparison.authenticated_profile}",
        f"- Profile mismatch: {str(comparison.profile_mismatch).lower()}",
        "",
        "## Version and Content",
        "",
        f"- Public x-ms-schemaVersion: {vc.old_x_ms_schema_version}",
        f"- Authenticated x-ms-schemaVersion: {vc.new_x_ms_schema_version}",
        f"- Schema version changed: {str(vc.schema_version_changed).lower()}",
        f"- Public sha256: {vc.old_sha256}",
        f"- Authenticated sha256: {vc.new_sha256}",
        f"- SHA-256 changed: {str(vc.sha256_changed).lower()}",
        "",
        "## Semantic Diff",
        "",
        f"- Semantic change count: {vc.semantic_change_count}",
        f"- Semantic changes present: {str(vc.semantic_changes_present).lower()}",
        "",
        "## Classification",
        "",
        f"- Version classification: `{vc.classification}`",
        "",
        "## Warnings",
        "",
    ]
    if comparison.warnings:
        for warning in comparison.warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("None.")
    return "\n".join(lines)


def render_source_comparison_json(comparison: SourceComparison) -> str:
    """Return deterministic JSON string. No I/O."""
    vc = comparison.version_comparison
    payload = {
        "report_type": "source_comparison",
        "comparison_kind": comparison.comparison_kind,
        "public_snapshot": str(comparison.public_snapshot),
        "authenticated_snapshot": str(comparison.authenticated_snapshot),
        "public_profile": comparison.public_profile,
        "authenticated_profile": comparison.authenticated_profile,
        "public_source_kind": comparison.public_source_kind,
        "authenticated_source_kind": comparison.authenticated_source_kind,
        "authenticated_auth_mode": comparison.authenticated_auth_mode,
        "authenticated_tenant_label": comparison.authenticated_tenant_label,
        "profile_mismatch": comparison.profile_mismatch,
        "warnings": list(comparison.warnings),
        "public_x_ms_schema_version": vc.old_x_ms_schema_version,
        "authenticated_x_ms_schema_version": vc.new_x_ms_schema_version,
        "schema_version_changed": vc.schema_version_changed,
        "public_sha256": vc.old_sha256,
        "authenticated_sha256": vc.new_sha256,
        "sha256_changed": vc.sha256_changed,
        "semantic_change_count": vc.semantic_change_count,
        "semantic_changes_present": vc.semantic_changes_present,
        "version_classification": vc.classification,
    }
    approved_payload = {field: payload[field] for field in JSON_SOURCE_COMPARISON_FIELDS}
    return json.dumps(approved_payload, indent=2)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _read_raw_sidecar(snapshot_path: Path) -> dict:
    sidecar_file = sidecar_path_for_snapshot(snapshot_path)
    try:
        raw = json.loads(sidecar_file.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SnapshotValidationError(f"missing sidecar: {sidecar_file}") from exc
    except json.JSONDecodeError as exc:
        raise SnapshotValidationError(f"invalid sidecar JSON: {sidecar_file}") from exc
    if not isinstance(raw, dict):
        raise SnapshotValidationError(f"sidecar must be a JSON object: {sidecar_file}")
    return raw


def _validate_public_provenance(raw: dict, snapshot_path: Path) -> str:
    """
    Return the effective source_kind for the public snapshot. Raises
    SnapshotValidationError for disallowed source_kind values.
    """
    source_kind = raw.get("source_kind")
    if source_kind is None:
        # Legacy public snapshot — no source_kind field is acceptable
        return "public_graph_metadata"
    if source_kind == "public_graph_metadata":
        return "public_graph_metadata"
    if source_kind == _VALID_AUTH_SOURCE_KIND:
        raise SnapshotValidationError(
            f"public snapshot has authenticated source_kind {source_kind!r}; "
            f"expected public_graph_metadata or no source_kind: {snapshot_path}"
        )
    raise SnapshotValidationError(
        f"public snapshot has unknown source_kind {source_kind!r}: {snapshot_path}"
    )


def _validate_auth_provenance(raw: dict, snapshot_path: Path) -> tuple[str, str | None, str | None]:
    """
    Return (source_kind, auth_mode, tenant_label) for the authenticated snapshot.
    Raises SnapshotValidationError for missing or invalid provenance.
    """
    source_kind = raw.get("source_kind")
    if source_kind is None:
        raise SnapshotValidationError(
            f"authenticated snapshot is missing required source_kind field: {snapshot_path}"
        )
    if source_kind != _VALID_AUTH_SOURCE_KIND:
        raise SnapshotValidationError(
            f"authenticated snapshot has unexpected source_kind {source_kind!r}; "
            f"expected {_VALID_AUTH_SOURCE_KIND!r}: {snapshot_path}"
        )

    auth_mode = raw.get("auth_mode")
    if auth_mode is None:
        raise SnapshotValidationError(
            f"authenticated snapshot is missing required auth_mode field: {snapshot_path}"
        )
    if auth_mode != _VALID_AUTH_MODE:
        raise SnapshotValidationError(
            f"authenticated snapshot has unexpected auth_mode {auth_mode!r}; "
            f"expected {_VALID_AUTH_MODE!r}: {snapshot_path}"
        )

    tenant_label = raw.get("tenant_label")
    # tenant_label may be a non-empty string or null (None)
    if tenant_label is not None and not isinstance(tenant_label, str):
        raise SnapshotValidationError(
            f"authenticated snapshot tenant_label must be a string or null: {snapshot_path}"
        )

    return source_kind, auth_mode, tenant_label
