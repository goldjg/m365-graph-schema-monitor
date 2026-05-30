from __future__ import annotations

from pathlib import Path

from graph_schema_monitor.parser import parse_csdl_file


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parser_extracts_expected_types_and_properties() -> None:
    snapshot = parse_csdl_file(FIXTURES_DIR / "schema_old.xml")

    assert "microsoft.graph.conditionalAccessPolicy" in snapshot.types
    assert "microsoft.graph.conditionalAccessConditionSet" in snapshot.types

    policy = snapshot.types["microsoft.graph.conditionalAccessPolicy"]
    assert list(policy.properties) == ["conditions", "displayName", "id", "state"]
    assert policy.properties["id"].nullable is False
    assert policy.properties["displayName"].nullable is True

    condition_set = snapshot.types["microsoft.graph.conditionalAccessConditionSet"]
    assert condition_set.properties["includeRoles"].is_collection is True
    assert condition_set.properties["includeRoles"].property_type == "Edm.String"


def test_parser_normalizes_nullable_default_true() -> None:
    old_snapshot = parse_csdl_file(FIXTURES_DIR / "schema_old.xml")
    new_snapshot = parse_csdl_file(FIXTURES_DIR / "schema_new.xml")

    old_display_name = old_snapshot.types["microsoft.graph.conditionalAccessPolicy"].properties["displayName"]
    new_display_name = new_snapshot.types["microsoft.graph.conditionalAccessPolicy"].properties["displayName"]

    assert old_display_name.nullable is True
    assert new_display_name.nullable is True
