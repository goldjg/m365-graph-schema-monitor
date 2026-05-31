from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from graph_schema_monitor.report import build_diff_report
from graph_schema_monitor.snapshots import SnapshotValidationError, sidecar_path_for_snapshot


FIXTURES_DIR = Path(__file__).parent / "fixtures"


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


def test_build_diff_report_renders_grouped_markdown_sections(tmp_path: Path) -> None:
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

    report = build_diff_report(old_snapshot, new_snapshot)

    assert report.startswith("# Graph Schema Diff Report")
    assert "## Metadata" in report
    assert "## Changes" in report
    assert "### Types Added" in report
    assert "### Types Removed" in report
    assert "### Properties Added" in report
    assert "### Properties Removed" in report
    assert "### Property Types Changed" in report
    assert "### Property Nullability Changed" in report
    assert "### Property Collection Shape Changed" in report
    assert "microsoft.graph.conditionalAccessPolicy.templateId" in report
    assert "microsoft.graph.conditionalAccessConditionSet.clientApplications" in report
    assert report.count("None.") == 5


def test_build_diff_report_supports_deterministic_json_output(tmp_path: Path) -> None:
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

    first = build_diff_report(old_snapshot, new_snapshot, output_format="json")
    second = build_diff_report(old_snapshot, new_snapshot, output_format="json")

    assert first == second
    payload = json.loads(first)
    assert payload["metadata"]["old_snapshot"]["profile"] == "v1.0"
    assert payload["metadata"]["new_snapshot"]["profile"] == "beta"
    assert any(
        item["change_type"] == "property_added" and item["property_name"] == "templateId"
        for item in payload["changes"]
    )


def test_build_diff_report_renders_unknown_metadata_for_missing_sidecar(tmp_path: Path) -> None:
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
    sidecar_path_for_snapshot(old_snapshot).unlink()

    report = build_diff_report(old_snapshot, new_snapshot)

    assert "- Profile: `unknown`" in report
    assert "- Fetched at (UTC): `unknown`" in report
    assert "- SHA-256: `unknown`" in report


def test_build_diff_report_fails_for_malformed_sidecar(tmp_path: Path) -> None:
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
    sidecar_path_for_snapshot(old_snapshot).write_text("{", encoding="utf-8")

    with pytest.raises(SnapshotValidationError, match="invalid sidecar JSON"):
        build_diff_report(old_snapshot, new_snapshot)


def test_build_diff_report_fails_for_missing_required_sidecar_field(tmp_path: Path) -> None:
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
    sidecar_path = sidecar_path_for_snapshot(old_snapshot)
    payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    payload.pop("sha256")
    sidecar_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with pytest.raises(SnapshotValidationError, match="sidecar missing required field\\(s\\): sha256"):
        build_diff_report(old_snapshot, new_snapshot)
