from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from graph_schema_monitor.diff import DiffChange, diff_snapshots
from graph_schema_monitor.report_filters import CHANGE_TYPE_ORDER
from graph_schema_monitor.snapshots import SnapshotBundle, SnapshotSidecar, load_snapshot_bundle, sidecar_path_for_snapshot
from graph_schema_monitor.watchlists import (
    JSON_WATCHLIST_REPORT_FIELDS,
    Watchlist,
    WatchlistValidationError,
    change_matches_watchlist,
    load_watchlist,
    match_watchlist,
    render_watchlist_json_report,
    render_watchlist_markdown_report,
    summarise_watchlist_matches,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "tests" / "fixtures"


def _write_watchlist(tmp_path: Path, payload: object, *, name: str = "watchlist.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _write_snapshot_with_sidecar(
    tmp_path: Path,
    *,
    name: str,
    fixture_name: str,
    profile: str,
    fetched_at_utc: str,
) -> Path:
    snapshot_path = tmp_path / name
    shutil.copyfile(FIXTURES_DIR / fixture_name, snapshot_path)
    sidecar_payload = {
        "profile": profile,
        "source_url": f"https://graph.microsoft.com/{profile}/$metadata",
        "fetched_at_utc": fetched_at_utc,
        "status_code": 200,
        "content_type": "application/xml; charset=utf-8",
        "etag": '"etag-1"',
        "last_modified": "Fri, 30 May 2026 20:00:00 GMT",
        "sha256": hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
        "x_ms_schema_version": "2026-05-30",
    }
    sidecar_path_for_snapshot(snapshot_path).write_text(json.dumps(sidecar_payload, indent=2), encoding="utf-8")
    return snapshot_path


def _load_bundles(tmp_path: Path) -> tuple[SnapshotBundle, SnapshotBundle, list[DiffChange]]:
    old_snapshot = _write_snapshot_with_sidecar(
        tmp_path,
        name="old.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T20:00:00Z",
    )
    new_snapshot = _write_snapshot_with_sidecar(
        tmp_path,
        name="new.xml",
        fixture_name="schema_new.xml",
        profile="beta",
        fetched_at_utc="2026-05-31T20:00:00Z",
    )
    old_bundle = load_snapshot_bundle(old_snapshot, allow_missing_sidecar=True)
    new_bundle = load_snapshot_bundle(new_snapshot, allow_missing_sidecar=True)
    return old_bundle, new_bundle, diff_snapshots(old_bundle.snapshot, new_bundle.snapshot)


def _sample_changes() -> list[DiffChange]:
    return [
        DiffChange(
            change_type="property_added",
            type_name="microsoft.graph.alpha.TypeOne",
            property_name="flag",
            old_value=None,
            new_value={"property_type": "Edm.String", "nullable": True, "is_collection": False},
        ),
        DiffChange(
            change_type="property_removed",
            type_name="microsoft.graph.beta.TypeTwo",
            property_name="flag",
            old_value={"property_type": "Edm.String", "nullable": True, "is_collection": False},
            new_value=None,
        ),
        DiffChange(
            change_type="type_added",
            type_name="microsoft.graph.alpha.TypeThree",
            property_name=None,
            old_value=None,
            new_value={"kind": "EntityType"},
        ),
    ]


def test_load_valid_watchlist() -> None:
    watchlist = load_watchlist(FIXTURES_DIR / "watchlist_identity.json")

    assert watchlist == Watchlist(
        name="identity-test",
        description=None,
        type_prefixes=("microsoft.graph.conditionalAccess",),
        change_types=("property_added", "property_removed"),
        type_names=(),
        property_names=(),
    )


def test_reject_non_object_watchlist_json(tmp_path: Path) -> None:
    path = _write_watchlist(tmp_path, ["bad"])

    with pytest.raises(WatchlistValidationError, match="watchlist must be a JSON object"):
        load_watchlist(path)


def test_reject_missing_name(tmp_path: Path) -> None:
    path = _write_watchlist(tmp_path, {"type_prefixes": ["microsoft.graph.conditionalAccess"]})

    with pytest.raises(WatchlistValidationError, match="watchlist name must be a non-empty string"):
        load_watchlist(path)


def test_reject_empty_name(tmp_path: Path) -> None:
    path = _write_watchlist(tmp_path, {"name": " ", "type_prefixes": ["microsoft.graph.conditionalAccess"]})

    with pytest.raises(WatchlistValidationError, match="watchlist name must be a non-empty string"):
        load_watchlist(path)


def test_reject_missing_both_type_prefixes_and_type_names() -> None:
    with pytest.raises(WatchlistValidationError, match="watchlist requires type_prefixes and/or type_names"):
        load_watchlist(FIXTURES_DIR / "watchlist_empty_prefixes.json")


def test_reject_unknown_change_type(tmp_path: Path) -> None:
    path = _write_watchlist(
        tmp_path,
        {
            "name": "bad",
            "type_prefixes": ["microsoft.graph.conditionalAccess"],
            "change_types": ["property_added", "nope"],
        },
    )

    with pytest.raises(WatchlistValidationError, match="watchlist contains unknown change type"):
        load_watchlist(path)


def test_reject_duplicate_list_values(tmp_path: Path) -> None:
    path = _write_watchlist(
        tmp_path,
        {"name": "bad", "type_prefixes": ["microsoft.graph.a", "microsoft.graph.a"]},
    )

    with pytest.raises(WatchlistValidationError, match="watchlist field contains duplicate value"):
        load_watchlist(path)


def test_reject_unexpected_fields(tmp_path: Path) -> None:
    path = _write_watchlist(
        tmp_path,
        {
            "name": "bad",
            "type_prefixes": ["microsoft.graph.a"],
            "severity": "high",
        },
    )

    with pytest.raises(WatchlistValidationError, match="watchlist contains unexpected field"):
        load_watchlist(path)


def test_reject_non_list_filter_field(tmp_path: Path) -> None:
    path = _write_watchlist(tmp_path, {"name": "bad", "type_prefixes": "microsoft.graph.a"})

    with pytest.raises(WatchlistValidationError, match="watchlist field must be a list"):
        load_watchlist(path)


def test_reject_empty_string_in_filter_list(tmp_path: Path) -> None:
    path = _write_watchlist(tmp_path, {"name": "bad", "type_prefixes": [""]})

    with pytest.raises(WatchlistValidationError, match="watchlist field must contain non-empty strings"):
        load_watchlist(path)


def test_match_by_type_prefix() -> None:
    watchlist = Watchlist("prefix", None, ("microsoft.graph.alpha",), (), (), ())

    assert change_matches_watchlist(_sample_changes()[0], watchlist) is True


def test_match_by_exact_type_name() -> None:
    watchlist = Watchlist("exact", None, (), (), ("microsoft.graph.beta.TypeTwo",), ())

    assert change_matches_watchlist(_sample_changes()[1], watchlist) is True


def test_match_by_change_type() -> None:
    watchlist = Watchlist("type", None, ("microsoft.graph.alpha",), ("property_added",), (), ())

    assert change_matches_watchlist(_sample_changes()[0], watchlist) is True
    assert change_matches_watchlist(_sample_changes()[2], watchlist) is False


def test_match_by_property_name() -> None:
    watchlist = Watchlist("property", None, ("microsoft.graph.alpha",), (), (), ("flag",))

    assert change_matches_watchlist(_sample_changes()[0], watchlist) is True


def test_or_within_type_prefixes() -> None:
    watchlist = Watchlist("prefixes", None, ("microsoft.graph.gamma", "microsoft.graph.beta"), (), (), ())

    assert change_matches_watchlist(_sample_changes()[1], watchlist) is True


def test_or_within_change_types() -> None:
    watchlist = Watchlist("changes", None, ("microsoft.graph.beta",), ("type_added", "property_removed"), (), ())

    assert change_matches_watchlist(_sample_changes()[1], watchlist) is True


def test_and_across_type_and_change_type_filters() -> None:
    watchlist = Watchlist("and", None, ("microsoft.graph.alpha",), ("property_removed",), (), ())

    assert change_matches_watchlist(_sample_changes()[0], watchlist) is False


def test_property_filter_does_not_match_type_level_changes_with_null_property_name() -> None:
    watchlist = Watchlist("property", None, ("microsoft.graph.alpha",), (), (), ("flag",))

    assert change_matches_watchlist(_sample_changes()[2], watchlist) is False


def test_match_watchlist_preserves_existing_order() -> None:
    changes = _sample_changes()
    watchlist = Watchlist("ordered", None, ("microsoft.graph",), ("property_added", "type_added"), (), ())

    matched = match_watchlist(changes, watchlist)

    assert [change.change_type for change in matched] == ["property_added", "type_added"]


def test_no_match_returns_empty_list() -> None:
    watchlist = Watchlist("none", None, ("microsoft.graph.zeta",), (), (), ())

    assert match_watchlist(_sample_changes(), watchlist) == []


def test_summarise_watchlist_matches_reports_zero_matches() -> None:
    summary = summarise_watchlist_matches(_sample_changes(), [])

    assert summary["total_changes"] == 3
    assert summary["matching_changes"] == 0
    assert summary["matches_by_change_type"] == {change_type: 0 for change_type in CHANGE_TYPE_ORDER}


def test_markdown_report_has_required_sections(tmp_path: Path) -> None:
    old_bundle, new_bundle, changes = _load_bundles(tmp_path)
    watchlist = load_watchlist(FIXTURES_DIR / "watchlist_identity.json")
    matching_changes = match_watchlist(changes, watchlist)

    report = render_watchlist_markdown_report(
        old_bundle,
        new_bundle,
        watchlist,
        FIXTURES_DIR / "watchlist_identity.json",
        changes,
        matching_changes,
    )

    assert "# Graph Schema Watchlist Report" in report
    assert "## Watchlist" in report
    assert "## Snapshots" in report
    assert "## Summary" in report
    assert "### Matches by Change Type" in report
    assert "## Matched Changes" in report
    assert "### Properties Added" in report


def test_markdown_report_no_match_message() -> None:
    bundle = SnapshotBundle(
        snapshot_path=Path("old.xml"),
        sidecar_path=Path("old.xml.json"),
        snapshot=load_snapshot_bundle(FIXTURES_DIR / "schema_old.xml", allow_missing_sidecar=True).snapshot,
        sidecar=None,
    )
    watchlist = Watchlist("none", None, ("microsoft.graph.zeta",), (), (), ())

    report = render_watchlist_markdown_report(bundle, bundle, watchlist, Path("watchlist.json"), _sample_changes(), [])

    assert "No matching watchlist changes." in report


def test_json_report_has_exact_approved_top_level_fields(tmp_path: Path) -> None:
    old_bundle, new_bundle, changes = _load_bundles(tmp_path)
    watchlist = load_watchlist(FIXTURES_DIR / "watchlist_identity.json")
    matching_changes = match_watchlist(changes, watchlist)

    report = render_watchlist_json_report(
        old_bundle,
        new_bundle,
        watchlist,
        FIXTURES_DIR / "watchlist_identity.json",
        changes,
        matching_changes,
    )

    payload = json.loads(report)
    assert list(payload.keys()) == list(JSON_WATCHLIST_REPORT_FIELDS)


def test_json_report_matches_by_change_type_includes_all_seven(tmp_path: Path) -> None:
    old_bundle, new_bundle, changes = _load_bundles(tmp_path)
    watchlist = load_watchlist(FIXTURES_DIR / "watchlist_identity.json")
    matching_changes = match_watchlist(changes, watchlist)

    payload = json.loads(
        render_watchlist_json_report(
            old_bundle,
            new_bundle,
            watchlist,
            FIXTURES_DIR / "watchlist_identity.json",
            changes,
            matching_changes,
        )
    )

    assert list(payload["matches_by_change_type"].keys()) == list(CHANGE_TYPE_ORDER)


def test_json_report_uses_null_for_missing_sidecar_fields() -> None:
    snapshot = load_snapshot_bundle(FIXTURES_DIR / "schema_old.xml", allow_missing_sidecar=True).snapshot
    bundle = SnapshotBundle(
        snapshot_path=Path("old.xml"),
        sidecar_path=Path("old.xml.json"),
        snapshot=snapshot,
        sidecar=None,
    )
    watchlist = Watchlist("none", None, ("microsoft.graph.alpha",), (), (), ())

    payload = json.loads(render_watchlist_json_report(bundle, bundle, watchlist, Path("watchlist.json"), [], []))

    assert payload["old_profile"] is None
    assert payload["old_fetched_at_utc"] is None
    assert payload["old_sha256"] is None
