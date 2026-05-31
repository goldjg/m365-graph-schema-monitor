from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .diff import DiffChange, diff_snapshots
from .snapshots import SnapshotBundle, load_snapshot_bundle


def build_diff_report(old_snapshot_path: str | Path, new_snapshot_path: str | Path) -> str:
    old_bundle = load_snapshot_bundle(old_snapshot_path)
    new_bundle = load_snapshot_bundle(new_snapshot_path)
    changes = diff_snapshots(old_bundle.snapshot, new_bundle.snapshot)
    return render_markdown_diff_report(old_bundle, new_bundle, changes)


def render_markdown_diff_report(
    old_bundle: SnapshotBundle,
    new_bundle: SnapshotBundle,
    changes: list[DiffChange],
) -> str:
    lines = ["# Graph schema diff report", "", "## Snapshots"]
    lines.extend(_render_snapshot_details("Old", old_bundle))
    lines.extend(["", *(_render_snapshot_details("New", new_bundle))])
    lines.extend(["", "## Summary"])
    lines.extend(_render_summary(changes))
    lines.extend(["", "## Changes"])

    if not changes:
        lines.append("No differences.")
        return "\n".join(lines)

    for change in changes:
        target = change.type_name if change.property_name is None else f"{change.type_name}.{change.property_name}"
        lines.append(
            "- "
            f"`[{change.change_type}]` `{target}`: "
            f"old=`{_format_value(change.old_value)}` new=`{_format_value(change.new_value)}`"
        )
    return "\n".join(lines)


def _render_snapshot_details(label: str, bundle: SnapshotBundle) -> list[str]:
    sidecar = bundle.sidecar
    return [
        f"- {label} snapshot: `{bundle.snapshot_path}`",
        f"  - Sidecar: `{bundle.sidecar_path}`",
        f"  - Profile: `{sidecar.profile}`",
        f"  - Source URL: `{sidecar.source_url}`",
        f"  - Fetched at (UTC): `{sidecar.fetched_at_utc}`",
        f"  - SHA-256: `{sidecar.sha256}`",
        f"  - Types: `{len(bundle.snapshot.types)}`",
    ]


def _render_summary(changes: list[DiffChange]) -> list[str]:
    change_counts = Counter(change.change_type for change in changes)
    touched_types = sorted({change.type_name for change in changes})
    lines = [
        f"- Total changes: `{len(changes)}`",
        f"- Types changed: `{len(touched_types)}`",
    ]
    for change_type in sorted(change_counts):
        lines.append(f"- {change_type}: `{change_counts[change_type]}`")
    return lines


def _format_value(value: Any) -> str:
    return json.dumps(value, sort_keys=True)
