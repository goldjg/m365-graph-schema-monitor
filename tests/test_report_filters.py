from __future__ import annotations

from graph_schema_monitor.diff import DiffChange
from graph_schema_monitor.report import CHANGE_GROUPS
from graph_schema_monitor.report_filters import filter_changes, summarise_changes


CHANGE_TYPES = tuple(change_type for change_type, _heading in CHANGE_GROUPS)


def _sample_changes() -> list[DiffChange]:
    return [
        DiffChange(
            change_type="property_added",
            type_name="microsoft.graph.conditionalAccessPolicy",
            property_name="templateId",
            old_value=None,
            new_value={"property_type": "Edm.String", "nullable": True, "is_collection": False},
        ),
        DiffChange(
            change_type="property_removed",
            type_name="microsoft.graph.user",
            property_name="legacyProp",
            old_value={"property_type": "Edm.String", "nullable": True, "is_collection": False},
            new_value=None,
        ),
        DiffChange(
            change_type="type_added",
            type_name="microsoft.graph.identityGovernance.workflow",
            property_name=None,
            old_value=None,
            new_value={"kind": "EntityType"},
        ),
        DiffChange(
            change_type="property_added",
            type_name="microsoft.graph.identityGovernance.workflowVersion",
            property_name="description",
            old_value=None,
            new_value={"property_type": "Edm.String", "nullable": True, "is_collection": False},
        ),
        DiffChange(
            change_type="property_added",
            type_name="microsoft.graph.identityGovernance.workflowTemplate",
            property_name="displayName",
            old_value=None,
            new_value={"property_type": "Edm.String", "nullable": True, "is_collection": False},
        ),
        DiffChange(
            change_type="property_nullability_changed",
            type_name="microsoft.graph.identityGovernance.workflowTemplate",
            property_name="isEnabled",
            old_value={"property_type": "Edm.Boolean", "nullable": True, "is_collection": False},
            new_value={"property_type": "Edm.Boolean", "nullable": False, "is_collection": False},
        ),
    ]


def test_filter_changes_by_change_type() -> None:
    filtered = filter_changes(_sample_changes(), change_type="property_added")

    assert len(filtered) == 3
    assert all(change.change_type == "property_added" for change in filtered)


def test_filter_changes_by_type_prefix() -> None:
    filtered = filter_changes(_sample_changes(), type_prefix="microsoft.graph.identityGovernance.workflow")

    assert [change.type_name for change in filtered] == [
        "microsoft.graph.identityGovernance.workflow",
        "microsoft.graph.identityGovernance.workflowVersion",
        "microsoft.graph.identityGovernance.workflowTemplate",
        "microsoft.graph.identityGovernance.workflowTemplate",
    ]
    assert all(not change.type_name.startswith("microsoft.graph.user") for change in filtered)


def test_filter_changes_by_type_name() -> None:
    filtered = filter_changes(_sample_changes(), type_name="microsoft.graph.identityGovernance.workflowTemplate")

    assert [change.property_name for change in filtered] == ["displayName", "isEnabled"]


def test_filter_changes_limit() -> None:
    filtered = filter_changes(_sample_changes(), limit=2)

    assert filtered == _sample_changes()[:2]


def test_filter_changes_combined() -> None:
    filtered = filter_changes(
        _sample_changes(),
        change_type="property_added",
        type_prefix="microsoft.graph.identityGovernance.workflow",
        limit=1,
    )

    assert len(filtered) == 1
    assert filtered[0].type_name == "microsoft.graph.identityGovernance.workflowVersion"


def test_filter_changes_empty_input() -> None:
    assert filter_changes([]) == []


def test_filter_changes_invalid_change_type_raises() -> None:
    try:
        filter_changes(_sample_changes(), change_type="not_real")
    except ValueError as exc:
        assert "Unrecognized change type" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_filter_changes_invalid_limit_raises() -> None:
    try:
        filter_changes(_sample_changes(), limit=0)
    except ValueError as exc:
        assert "positive integer" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_summarise_changes_key_order() -> None:
    summary = summarise_changes(_sample_changes())

    assert tuple(summary) == ("total_changes", "by_change_type", "top_type_prefixes")


def test_summarise_changes_counts() -> None:
    summary = summarise_changes(_sample_changes())

    assert tuple(summary["by_change_type"]) == CHANGE_TYPES
    assert summary["by_change_type"] == {
        "type_added": 1,
        "type_removed": 0,
        "property_added": 3,
        "property_removed": 1,
        "property_type_changed": 0,
        "property_nullability_changed": 1,
        "property_collection_shape_changed": 0,
    }


def test_summarise_changes_top_prefixes() -> None:
    summary = summarise_changes(_sample_changes())

    assert summary["top_type_prefixes"] == [
        {"prefix": "microsoft.graph.identityGovernance", "count": 4},
        {"prefix": "microsoft.graph.conditionalAccessPolicy", "count": 1},
        {"prefix": "microsoft.graph.user", "count": 1},
    ]


def test_summarise_changes_empty() -> None:
    summary = summarise_changes([])

    assert summary["total_changes"] == 0
    assert summary["by_change_type"] == {change_type: 0 for change_type in CHANGE_TYPES}
    assert summary["top_type_prefixes"] == []
