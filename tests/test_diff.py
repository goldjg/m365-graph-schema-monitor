from __future__ import annotations

from pathlib import Path

from graph_schema_monitor.diff import changes_to_json, diff_snapshots
from graph_schema_monitor.parser import PropertyInfo, SchemaSnapshot, TypeInfo, parse_csdl_file


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _single_type_snapshot(property_info: PropertyInfo) -> SchemaSnapshot:
    type_name = "microsoft.graph.sampleType"
    return SchemaSnapshot(
        types={
            type_name: TypeInfo(
                namespace="microsoft.graph",
                name="sampleType",
                full_name=type_name,
                kind="EntityType",
                properties={"sampleProperty": property_info},
            )
        }
    )


def test_diff_detects_expected_added_properties() -> None:
    old_snapshot = parse_csdl_file(FIXTURES_DIR / "schema_old.xml")
    new_snapshot = parse_csdl_file(FIXTURES_DIR / "schema_new.xml")

    policy_changes = diff_snapshots(
        old_snapshot,
        new_snapshot,
        type_name="microsoft.graph.conditionalAccessPolicy",
    )
    condition_changes = diff_snapshots(
        old_snapshot,
        new_snapshot,
        type_name="microsoft.graph.conditionalAccessConditionSet",
    )

    policy_added = [c for c in policy_changes if c.change_type == "property_added"]
    condition_added = [c for c in condition_changes if c.change_type == "property_added"]

    assert [c.property_name for c in policy_added] == ["templateId"]
    assert [c.property_name for c in condition_added] == ["clientApplications"]


def test_diff_ignores_nullable_true_default_vs_explicit_true() -> None:
    old_snapshot = parse_csdl_file(FIXTURES_DIR / "schema_old.xml")
    new_snapshot = parse_csdl_file(FIXTURES_DIR / "schema_new.xml")

    changes = diff_snapshots(
        old_snapshot,
        new_snapshot,
        type_name="microsoft.graph.conditionalAccessPolicy",
    )
    assert not any(
        c.change_type == "property_nullability_changed" and c.property_name == "displayName"
        for c in changes
    )


def test_diff_detects_type_nullability_and_collection_shape_changes() -> None:
    old_snapshot = _single_type_snapshot(
        PropertyInfo(
            name="sampleProperty",
            property_type="Edm.String",
            nullable=True,
            is_collection=False,
        )
    )
    new_snapshot = _single_type_snapshot(
        PropertyInfo(
            name="sampleProperty",
            property_type="Edm.Int32",
            nullable=False,
            is_collection=True,
        )
    )

    changes = diff_snapshots(old_snapshot, new_snapshot)
    assert [c.change_type for c in changes] == [
        "property_collection_shape_changed",
        "property_nullability_changed",
        "property_type_changed",
    ]
    assert changes_to_json(changes)[0]["type_name"] == "microsoft.graph.sampleType"
