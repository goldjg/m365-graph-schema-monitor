from __future__ import annotations

from collections import Counter
from typing import Any

from .diff import DiffChange


CHANGE_TYPE_ORDER = (
    "type_added",
    "type_removed",
    "property_added",
    "property_removed",
    "property_type_changed",
    "property_nullability_changed",
    "property_collection_shape_changed",
)
VALID_CHANGE_TYPES = frozenset(CHANGE_TYPE_ORDER)


def filter_changes(
    changes: list[DiffChange],
    *,
    change_type: str | None = None,
    type_prefix: str | None = None,
    type_name: str | None = None,
    limit: int | None = None,
) -> list[DiffChange]:
    if change_type is not None and change_type not in VALID_CHANGE_TYPES:
        raise ValueError(f"Unrecognized change type: {change_type}")
    if limit is not None and limit <= 0:
        raise ValueError("limit must be a positive integer")

    filtered = changes
    if change_type is not None:
        filtered = [change for change in filtered if change.change_type == change_type]
    if type_prefix is not None:
        filtered = [change for change in filtered if change.type_name.startswith(type_prefix)]
    if type_name is not None:
        filtered = [change for change in filtered if change.type_name == type_name]
    if limit is not None:
        filtered = filtered[:limit]
    return filtered


def summarise_changes(changes: list[DiffChange]) -> dict[str, Any]:
    change_counts = Counter(change.change_type for change in changes)
    prefix_counts = Counter(_derive_type_prefix(change.type_name) for change in changes)
    top_type_prefixes = [
        {"prefix": prefix, "count": count}
        for prefix, count in sorted(prefix_counts.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]
    by_change_type = {change_type: change_counts.get(change_type, 0) for change_type in CHANGE_TYPE_ORDER}
    return {
        "total_changes": len(changes),
        "by_change_type": by_change_type,
        "top_type_prefixes": top_type_prefixes,
    }


def _derive_type_prefix(type_name: str) -> str:
    parts = type_name.split(".")
    if len(parts) <= 3:
        return type_name
    return ".".join(parts[:3])
