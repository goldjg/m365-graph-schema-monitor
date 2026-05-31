from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .diff import diff_snapshots
from .snapshots import SnapshotValidationError, load_snapshot_bundle


JSON_VERSION_COMPARISON_REPORT_FIELDS = (
    "report_type",
    "old_snapshot",
    "new_snapshot",
    "old_profile",
    "new_profile",
    "old_fetched_at_utc",
    "new_fetched_at_utc",
    "old_sha256",
    "new_sha256",
    "old_x_ms_schema_version",
    "new_x_ms_schema_version",
    "schema_version_changed",
    "sha256_changed",
    "semantic_change_count",
    "semantic_changes_present",
    "classification",
)


@dataclass(frozen=True)
class VersionComparison:
    old_snapshot: Path
    new_snapshot: Path
    old_profile: str | None
    new_profile: str | None
    old_fetched_at_utc: str | None
    new_fetched_at_utc: str | None
    old_sha256: str
    new_sha256: str
    old_x_ms_schema_version: str
    new_x_ms_schema_version: str
    schema_version_changed: bool
    sha256_changed: bool
    semantic_change_count: int
    semantic_changes_present: bool
    classification: str


def build_version_comparison(
    old_snapshot_path: str | Path,
    new_snapshot_path: str | Path,
) -> VersionComparison:
    """
    Load two local snapshot bundles (sidecars required), validate
    provenance, compute semantic diff, and return a frozen
    VersionComparison. Raises SnapshotValidationError for any
    missing or invalid provenance.
    """
    old_path = Path(old_snapshot_path)
    new_path = Path(new_snapshot_path)

    old_bundle = load_snapshot_bundle(old_path)
    new_bundle = load_snapshot_bundle(new_path)

    assert old_bundle.sidecar is not None
    assert new_bundle.sidecar is not None

    old_xmsv = old_bundle.sidecar.x_ms_schema_version
    if not old_xmsv:
        raise SnapshotValidationError(
            f"sidecar x_ms_schema_version is required for version comparison: {old_path}"
        )

    new_xmsv = new_bundle.sidecar.x_ms_schema_version
    if not new_xmsv:
        raise SnapshotValidationError(
            f"sidecar x_ms_schema_version is required for version comparison: {new_path}"
        )

    old_sha256 = old_bundle.sidecar.sha256
    new_sha256 = new_bundle.sidecar.sha256

    changes = diff_snapshots(old_bundle.snapshot, new_bundle.snapshot)
    semantic_change_count = len(changes)
    semantic_changes_present = semantic_change_count > 0
    schema_version_changed = old_xmsv != new_xmsv
    sha256_changed = old_sha256 != new_sha256
    classification = classify_version_comparison(
        schema_version_changed=schema_version_changed,
        sha256_changed=sha256_changed,
        semantic_changes_present=semantic_changes_present,
    )

    return VersionComparison(
        old_snapshot=old_path,
        new_snapshot=new_path,
        old_profile=old_bundle.sidecar.profile,
        new_profile=new_bundle.sidecar.profile,
        old_fetched_at_utc=old_bundle.sidecar.fetched_at_utc,
        new_fetched_at_utc=new_bundle.sidecar.fetched_at_utc,
        old_sha256=old_sha256,
        new_sha256=new_sha256,
        old_x_ms_schema_version=old_xmsv,
        new_x_ms_schema_version=new_xmsv,
        schema_version_changed=schema_version_changed,
        sha256_changed=sha256_changed,
        semantic_change_count=semantic_change_count,
        semantic_changes_present=semantic_changes_present,
        classification=classification,
    )


def classify_version_comparison(
    *,
    schema_version_changed: bool,
    sha256_changed: bool,
    semantic_changes_present: bool,
) -> str:
    """Return deterministic classification string. No side effects."""
    if not schema_version_changed and not sha256_changed and not semantic_changes_present:
        return "version_same_content_same_semantics_same"
    if not schema_version_changed and not sha256_changed and semantic_changes_present:
        return "version_same_content_same_semantics_changed"
    if not schema_version_changed and sha256_changed and not semantic_changes_present:
        return "version_same_content_changed_semantics_same"
    if not schema_version_changed and sha256_changed and semantic_changes_present:
        return "version_same_content_changed_semantics_changed"
    if schema_version_changed and not sha256_changed and not semantic_changes_present:
        return "version_changed_content_same_semantics_same"
    if schema_version_changed and not sha256_changed and semantic_changes_present:
        return "version_changed_content_same_semantics_changed"
    if schema_version_changed and sha256_changed and not semantic_changes_present:
        return "version_changed_content_changed_semantics_same"
    if schema_version_changed and sha256_changed and semantic_changes_present:
        return "version_changed_content_changed_semantics_changed"
    raise ValueError(
        f"Unexpected combination: schema_version_changed={schema_version_changed}, "
        f"sha256_changed={sha256_changed}, semantic_changes_present={semantic_changes_present}"
    )


def render_version_comparison_markdown(comparison: VersionComparison) -> str:
    """Return deterministic Markdown string. No I/O."""
    lines = [
        "# Graph Schema Version Comparison",
        "",
        "## Snapshots",
        "",
        f"- Old snapshot: {comparison.old_snapshot}",
        f"- New snapshot: {comparison.new_snapshot}",
        f"- Old profile: {comparison.old_profile}",
        f"- New profile: {comparison.new_profile}",
        f"- Old fetched at (UTC): {comparison.old_fetched_at_utc}",
        f"- New fetched at (UTC): {comparison.new_fetched_at_utc}",
        "",
        "## Provenance",
        "",
        "| Field | Old | New |",
        "|---|---|---|",
        f"| x-ms-schemaVersion | {comparison.old_x_ms_schema_version} | {comparison.new_x_ms_schema_version} |",
        f"| SHA-256 | {comparison.old_sha256} | {comparison.new_sha256} |",
        "",
        "## Change Detection",
        "",
        "| Dimension | Changed |",
        "|---|---|",
        f"| Schema version | {'yes' if comparison.schema_version_changed else 'no'} |",
        f"| Content (SHA-256) | {'yes' if comparison.sha256_changed else 'no'} |",
        f"| Semantic (parsed diff) | {'yes' if comparison.semantic_changes_present else 'no'} |",
        "",
        f"Semantic changes detected: {comparison.semantic_change_count}",
        "",
        "## Classification",
        "",
        f"`{comparison.classification}`",
    ]
    return "\n".join(lines)


def render_version_comparison_json(comparison: VersionComparison) -> str:
    """Return deterministic JSON string. No I/O."""
    payload = {
        "report_type": "version_comparison",
        "old_snapshot": str(comparison.old_snapshot),
        "new_snapshot": str(comparison.new_snapshot),
        "old_profile": comparison.old_profile,
        "new_profile": comparison.new_profile,
        "old_fetched_at_utc": comparison.old_fetched_at_utc,
        "new_fetched_at_utc": comparison.new_fetched_at_utc,
        "old_sha256": comparison.old_sha256,
        "new_sha256": comparison.new_sha256,
        "old_x_ms_schema_version": comparison.old_x_ms_schema_version,
        "new_x_ms_schema_version": comparison.new_x_ms_schema_version,
        "schema_version_changed": comparison.schema_version_changed,
        "sha256_changed": comparison.sha256_changed,
        "semantic_change_count": comparison.semantic_change_count,
        "semantic_changes_present": comparison.semantic_changes_present,
        "classification": comparison.classification,
    }
    approved_payload = {field: payload[field] for field in JSON_VERSION_COMPARISON_REPORT_FIELDS}
    return json.dumps(approved_payload, indent=2)
