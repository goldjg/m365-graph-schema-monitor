from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .diff import DiffChange, changes_to_json, diff_snapshots
from .snapshots import SnapshotBundle, load_snapshot_bundle


CHANGE_GROUPS = (
    ("type_added", "Types Added"),
    ("type_removed", "Types Removed"),
    ("property_added", "Properties Added"),
    ("property_removed", "Properties Removed"),
    ("property_type_changed", "Property Types Changed"),
    ("property_nullability_changed", "Property Nullability Changed"),
    ("property_collection_shape_changed", "Property Collection Shape Changed"),
)

JSON_DIFF_REPORT_FIELDS = (
    "report_type",
    "old_snapshot",
    "new_snapshot",
    "old_profile",
    "new_profile",
    "old_fetched_at_utc",
    "new_fetched_at_utc",
    "old_sha256",
    "new_sha256",
    "total_changes",
    "changes",
)


def build_diff_report(
    old_snapshot_path: str | Path,
    new_snapshot_path: str | Path,
    *,
    output_format: str = "markdown",
) -> str:
    old_bundle = load_snapshot_bundle(old_snapshot_path, allow_missing_sidecar=True)
    new_bundle = load_snapshot_bundle(new_snapshot_path, allow_missing_sidecar=True)
    changes = diff_snapshots(old_bundle.snapshot, new_bundle.snapshot)
    if output_format == "json":
        return render_json_diff_report(old_bundle, new_bundle, changes)
    return render_markdown_diff_report(old_bundle, new_bundle, changes)


def render_markdown_diff_report(
    old_bundle: SnapshotBundle,
    new_bundle: SnapshotBundle,
    changes: list[DiffChange],
) -> str:
    lines = ["# Graph Schema Diff Report", "", "## Metadata", ""]
    lines.extend(_render_snapshot_details("Old Snapshot", old_bundle))
    lines.extend(["", *(_render_snapshot_details("New Snapshot", new_bundle)), "", "## Changes"])

    if not changes:
        lines.append("No differences.")
        return "\n".join(lines)

    grouped_changes = {change_type: [] for change_type, _heading in CHANGE_GROUPS}
    for change in changes:
        grouped_changes[change.change_type].append(change)

    for change_type, heading in CHANGE_GROUPS:
        lines.extend(["", f"### {heading}"])
        group = grouped_changes[change_type]
        if not group:
            lines.extend(["", "None."])
            continue
        lines.append("")
        lines.extend(_render_group(change_type, group))
    return "\n".join(lines)


def _render_snapshot_details(label: str, bundle: SnapshotBundle) -> list[str]:
    sidecar = bundle.sidecar
    return [
        f"### {label}",
        f"- Snapshot Path: `{bundle.snapshot_path}`",
        f"- Sidecar Path: `{bundle.sidecar_path}`",
        f"- Profile: `{_render_string(sidecar.profile if sidecar is not None else None)}`",
        f"- Source URL: `{_render_string(sidecar.source_url if sidecar is not None else None)}`",
        f"- Fetched at (UTC): `{_render_string(sidecar.fetched_at_utc if sidecar is not None else None)}`",
        f"- SHA-256: `{_render_string(sidecar.sha256 if sidecar is not None else None)}`",
        f"- Types: `{len(bundle.snapshot.types)}`",
    ]


def render_json_diff_report(
    old_bundle: SnapshotBundle,
    new_bundle: SnapshotBundle,
    changes: list[DiffChange],
) -> str:
    old_sidecar = old_bundle.sidecar
    new_sidecar = new_bundle.sidecar
    payload = {
        "report_type": "schema_diff",
        "old_snapshot": str(old_bundle.snapshot_path),
        "new_snapshot": str(new_bundle.snapshot_path),
        "old_profile": None if old_sidecar is None else old_sidecar.profile,
        "new_profile": None if new_sidecar is None else new_sidecar.profile,
        "old_fetched_at_utc": None if old_sidecar is None else old_sidecar.fetched_at_utc,
        "new_fetched_at_utc": None if new_sidecar is None else new_sidecar.fetched_at_utc,
        "old_sha256": None if old_sidecar is None else old_sidecar.sha256,
        "new_sha256": None if new_sidecar is None else new_sidecar.sha256,
        "total_changes": len(changes),
        "changes": changes_to_json(changes),
    }
    approved_payload = {field: payload[field] for field in JSON_DIFF_REPORT_FIELDS}
    return json.dumps(approved_payload, indent=2)


def _format_value(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _render_group(change_type: str, changes: list[DiffChange]) -> list[str]:
    if change_type in {"type_added", "type_removed"}:
        lines: list[str] = []
        for change in changes:
            value = change.new_value if change.old_value is None else change.old_value
            lines.append(f"- `{change.type_name}`: `{_format_value(value)}`")
        return lines

    return [
        "- "
        f"`{change.type_name}.{change.property_name}`: "
        f"old=`{_format_value(change.old_value)}` new=`{_format_value(change.new_value)}`"
        for change in changes
    ]


def _render_string(value: str | None) -> str:
    return "unknown" if value is None else value
