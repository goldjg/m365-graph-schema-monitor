from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .parser import PropertyInfo, SchemaSnapshot


@dataclass(frozen=True)
class DiffChange:
    change_type: str
    type_name: str
    property_name: str | None
    old_value: Any
    new_value: Any


def _property_payload(prop: PropertyInfo | None) -> dict[str, Any] | None:
    if prop is None:
        return None
    return {
        "property_type": prop.property_type,
        "nullable": prop.nullable,
        "is_collection": prop.is_collection,
    }


def diff_snapshots(
    old_snapshot: SchemaSnapshot,
    new_snapshot: SchemaSnapshot,
    type_name: str | None = None,
) -> list[DiffChange]:
    if type_name:
        all_types = [type_name]
    else:
        all_types = sorted(set(old_snapshot.types).union(new_snapshot.types))

    changes: list[DiffChange] = []
    for current_type in all_types:
        old_type = old_snapshot.types.get(current_type)
        new_type = new_snapshot.types.get(current_type)

        if old_type is None and new_type is not None:
            changes.append(
                DiffChange(
                    change_type="type_added",
                    type_name=current_type,
                    property_name=None,
                    old_value=None,
                    new_value={"kind": new_type.kind},
                )
            )
            continue

        if old_type is not None and new_type is None:
            changes.append(
                DiffChange(
                    change_type="type_removed",
                    type_name=current_type,
                    property_name=None,
                    old_value={"kind": old_type.kind},
                    new_value=None,
                )
            )
            continue

        assert old_type is not None and new_type is not None
        all_properties = sorted(set(old_type.properties).union(new_type.properties))
        for property_name in all_properties:
            old_prop = old_type.properties.get(property_name)
            new_prop = new_type.properties.get(property_name)

            if old_prop is None and new_prop is not None:
                changes.append(
                    DiffChange(
                        change_type="property_added",
                        type_name=current_type,
                        property_name=property_name,
                        old_value=None,
                        new_value=_property_payload(new_prop),
                    )
                )
                continue

            if old_prop is not None and new_prop is None:
                changes.append(
                    DiffChange(
                        change_type="property_removed",
                        type_name=current_type,
                        property_name=property_name,
                        old_value=_property_payload(old_prop),
                        new_value=None,
                    )
                )
                continue

            assert old_prop is not None and new_prop is not None
            if old_prop.property_type != new_prop.property_type:
                changes.append(
                    DiffChange(
                        change_type="property_type_changed",
                        type_name=current_type,
                        property_name=property_name,
                        old_value=old_prop.property_type,
                        new_value=new_prop.property_type,
                    )
                )
            if old_prop.nullable != new_prop.nullable:
                changes.append(
                    DiffChange(
                        change_type="property_nullability_changed",
                        type_name=current_type,
                        property_name=property_name,
                        old_value=old_prop.nullable,
                        new_value=new_prop.nullable,
                    )
                )
            if old_prop.is_collection != new_prop.is_collection:
                changes.append(
                    DiffChange(
                        change_type="property_collection_shape_changed",
                        type_name=current_type,
                        property_name=property_name,
                        old_value=old_prop.is_collection,
                        new_value=new_prop.is_collection,
                    )
                )

    return sorted(
        changes,
        key=lambda c: (
            c.type_name,
            "" if c.property_name is None else c.property_name,
            c.change_type,
        ),
    )


def changes_to_json(changes: list[DiffChange]) -> list[dict[str, Any]]:
    return [
        {
            "change_type": c.change_type,
            "type_name": c.type_name,
            "property_name": c.property_name,
            "old_value": c.old_value,
            "new_value": c.new_value,
        }
        for c in changes
    ]


def render_changes_text(changes: list[DiffChange]) -> str:
    if not changes:
        return "No differences."

    lines: list[str] = []
    for change in changes:
        if change.property_name is None:
            lines.append(
                f"[{change.change_type}] {change.type_name}: "
                f"old={change.old_value} new={change.new_value}"
            )
            continue
        lines.append(
            f"[{change.change_type}] {change.type_name}.{change.property_name}: "
            f"old={change.old_value} new={change.new_value}"
        )
    return "\n".join(lines)
