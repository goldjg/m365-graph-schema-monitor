from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .diff import DiffChange, changes_to_json
from .report import CHANGE_GROUPS
from .report_filters import CHANGE_TYPE_ORDER, VALID_CHANGE_TYPES
from .snapshots import SnapshotBundle

WATCHLIST_FIELDS = frozenset(
    {
        "name",
        "description",
        "type_prefixes",
        "change_types",
        "type_names",
        "property_names",
    }
)

JSON_WATCHLIST_REPORT_FIELDS = (
    "report_type",
    "watchlist_name",
    "watchlist_description",
    "watchlist_path",
    "old_snapshot",
    "new_snapshot",
    "old_profile",
    "new_profile",
    "old_fetched_at_utc",
    "new_fetched_at_utc",
    "old_sha256",
    "new_sha256",
    "total_changes",
    "matching_changes",
    "matches_by_change_type",
    "matched_changes",
)


class WatchlistValidationError(Exception):
    exit_code = 2


@dataclass(frozen=True)
class Watchlist:
    name: str
    description: str | None
    type_prefixes: tuple[str, ...]
    change_types: tuple[str, ...]
    type_names: tuple[str, ...]
    property_names: tuple[str, ...]


def load_watchlist(path: str | Path) -> Watchlist:
    watchlist_path = Path(path)
    if not watchlist_path.exists() or not watchlist_path.is_file():
        raise WatchlistValidationError(f"Watchlist file does not exist: {watchlist_path}")
    try:
        payload = json.loads(watchlist_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WatchlistValidationError(f"invalid watchlist JSON: {watchlist_path}") from exc
    except OSError as exc:
        raise WatchlistValidationError(f"Failed to read watchlist file: {watchlist_path}") from exc
    return validate_watchlist_payload(payload, path=watchlist_path)


def validate_watchlist_payload(payload: object, *, path: Path) -> Watchlist:
    if not isinstance(payload, dict):
        raise WatchlistValidationError(f"watchlist must be a JSON object: {path}")

    unexpected_fields = sorted(field for field in payload if field not in WATCHLIST_FIELDS)
    if unexpected_fields:
        extras = ", ".join(unexpected_fields)
        raise WatchlistValidationError(f"watchlist contains unexpected field(s): {extras}: {path}")

    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise WatchlistValidationError(f"watchlist name must be a non-empty string: {path}")

    description = payload.get("description")
    if description is not None and not isinstance(description, str):
        raise WatchlistValidationError(f"watchlist description must be a string: {path}")

    type_prefixes = _validate_string_list(payload, "type_prefixes", path, required=False)
    type_names = _validate_string_list(payload, "type_names", path, required=False)
    change_types = _validate_string_list(payload, "change_types", path, required=False)
    property_names = _validate_string_list(payload, "property_names", path, required=False)

    if not type_prefixes and not type_names:
        raise WatchlistValidationError(f"watchlist requires type_prefixes and/or type_names: {path}")

    invalid_change_types = sorted(change_type for change_type in change_types if change_type not in VALID_CHANGE_TYPES)
    if invalid_change_types:
        invalid = ", ".join(invalid_change_types)
        raise WatchlistValidationError(f"watchlist contains unknown change type(s): {invalid}: {path}")

    return Watchlist(
        name=name,
        description=description,
        type_prefixes=tuple(type_prefixes),
        change_types=tuple(change_types),
        type_names=tuple(type_names),
        property_names=tuple(property_names),
    )


def change_matches_watchlist(change: DiffChange, watchlist: Watchlist) -> bool:
    type_matches = (
        change.type_name in watchlist.type_names
        or any(change.type_name.startswith(prefix) for prefix in watchlist.type_prefixes)
    )
    if not type_matches:
        return False

    if watchlist.change_types and change.change_type not in watchlist.change_types:
        return False

    if not watchlist.property_names:
        return True

    return change.property_name is not None and change.property_name in watchlist.property_names


def match_watchlist(changes: list[DiffChange], watchlist: Watchlist) -> list[DiffChange]:
    return [change for change in changes if change_matches_watchlist(change, watchlist)]


def summarise_watchlist_matches(
    all_changes: list[DiffChange],
    matching_changes: list[DiffChange],
) -> dict[str, Any]:
    counts = Counter(change.change_type for change in matching_changes)
    return {
        "total_changes": len(all_changes),
        "matching_changes": len(matching_changes),
        "matches_by_change_type": {change_type: counts.get(change_type, 0) for change_type in CHANGE_TYPE_ORDER},
    }


def render_watchlist_markdown_report(
    old_bundle: SnapshotBundle,
    new_bundle: SnapshotBundle,
    watchlist: Watchlist,
    watchlist_path: str | Path,
    all_changes: list[DiffChange],
    matching_changes: list[DiffChange],
) -> str:
    summary = summarise_watchlist_matches(all_changes, matching_changes)
    lines = [
        "# Graph Schema Watchlist Report",
        "",
        "## Watchlist",
        f"- Name: {watchlist.name}",
        f"- Description: {_render_markdown_value(watchlist.description)}",
        f"- Watchlist path: {watchlist_path}",
        "",
        "## Snapshots",
        f"- Old snapshot: {old_bundle.snapshot_path}",
        f"- New snapshot: {new_bundle.snapshot_path}",
        f"- Old profile: {_render_markdown_value(_sidecar_attr(old_bundle, 'profile'))}",
        f"- New profile: {_render_markdown_value(_sidecar_attr(new_bundle, 'profile'))}",
        f"- Old fetched_at_utc: {_render_markdown_value(_sidecar_attr(old_bundle, 'fetched_at_utc'))}",
        f"- New fetched_at_utc: {_render_markdown_value(_sidecar_attr(new_bundle, 'fetched_at_utc'))}",
        f"- Old sha256: {_render_markdown_value(_sidecar_attr(old_bundle, 'sha256'))}",
        f"- New sha256: {_render_markdown_value(_sidecar_attr(new_bundle, 'sha256'))}",
        "",
        "## Summary",
        f"- Total changes: {summary['total_changes']}",
        f"- Matching changes: {summary['matching_changes']}",
        "",
        "### Matches by Change Type",
        "",
        "| Change Type | Count |",
        "|---|---|",
    ]
    for change_type in CHANGE_TYPE_ORDER:
        lines.append(f"| {change_type} | {summary['matches_by_change_type'][change_type]} |")

    if not matching_changes:
        lines.extend(["", "No matching watchlist changes."])
        return "\n".join(lines)

    grouped_changes = {change_type: [] for change_type, _heading in CHANGE_GROUPS}
    for change in matching_changes:
        grouped_changes[change.change_type].append(change)

    lines.extend(["", "## Matched Changes"])
    for change_type, heading in CHANGE_GROUPS:
        lines.extend(["", f"### {heading}"])
        group = grouped_changes[change_type]
        if not group:
            lines.extend(["", "None."])
            continue
        lines.append("")
        lines.extend(_render_group(change_type, group))
    return "\n".join(lines)


def render_watchlist_json_report(
    old_bundle: SnapshotBundle,
    new_bundle: SnapshotBundle,
    watchlist: Watchlist,
    watchlist_path: str | Path,
    all_changes: list[DiffChange],
    matching_changes: list[DiffChange],
) -> str:
    summary = summarise_watchlist_matches(all_changes, matching_changes)
    payload = {
        "report_type": "schema_watchlist",
        "watchlist_name": watchlist.name,
        "watchlist_description": watchlist.description,
        "watchlist_path": str(watchlist_path),
        "old_snapshot": str(old_bundle.snapshot_path),
        "new_snapshot": str(new_bundle.snapshot_path),
        "old_profile": _sidecar_attr(old_bundle, "profile"),
        "new_profile": _sidecar_attr(new_bundle, "profile"),
        "old_fetched_at_utc": _sidecar_attr(old_bundle, "fetched_at_utc"),
        "new_fetched_at_utc": _sidecar_attr(new_bundle, "fetched_at_utc"),
        "old_sha256": _sidecar_attr(old_bundle, "sha256"),
        "new_sha256": _sidecar_attr(new_bundle, "sha256"),
        "total_changes": summary["total_changes"],
        "matching_changes": summary["matching_changes"],
        "matches_by_change_type": summary["matches_by_change_type"],
        "matched_changes": changes_to_json(matching_changes),
    }
    approved_payload = {field: payload[field] for field in JSON_WATCHLIST_REPORT_FIELDS}
    return json.dumps(approved_payload, indent=2)


def _validate_string_list(
    payload: dict[str, object],
    field_name: str,
    path: Path,
    *,
    required: bool,
) -> list[str]:
    if field_name not in payload:
        if required:
            raise WatchlistValidationError(f"watchlist missing required field: {field_name}: {path}")
        return []

    value = payload[field_name]
    if not isinstance(value, list):
        raise WatchlistValidationError(f"watchlist field must be a list: {field_name}: {path}")
    if not value:
        raise WatchlistValidationError(f"watchlist field must not be empty: {field_name}: {path}")

    items: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise WatchlistValidationError(f"watchlist field must contain non-empty strings: {field_name}: {path}")
        if item in seen:
            raise WatchlistValidationError(f"watchlist field contains duplicate value: {field_name}: {item}: {path}")
        seen.add(item)
        items.append(item)
    return items


def _sidecar_attr(bundle: SnapshotBundle, attribute: str) -> str | None:
    if bundle.sidecar is None:
        return None
    return getattr(bundle.sidecar, attribute)


def _render_markdown_value(value: str | None) -> str:
    return "unknown" if value is None else value


def _format_value(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _render_group(change_type: str, changes: list[DiffChange]) -> list[str]:
    if change_type in {"type_added", "type_removed"}:
        return [
            f"- `{change.type_name}`: `{_format_value(change.new_value if change.old_value is None else change.old_value)}`"
            for change in changes
        ]

    return [
        "- "
        f"`{change.type_name}.{change.property_name}`: "
        f"old=`{_format_value(change.old_value)}` new=`{_format_value(change.new_value)}`"
        for change in changes
    ]
