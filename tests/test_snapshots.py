from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from graph_schema_monitor.snapshots import (
    SnapshotValidationError,
    inspect_snapshot_directory,
    load_snapshot_bundle,
    render_snapshot_list,
    render_snapshot_validation,
    sidecar_path_for_snapshot,
)


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


def test_snapshot_inventory_lists_sorted_records(tmp_path: Path) -> None:
    _write_snapshot_with_sidecar(
        tmp_path,
        name="zeta.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T20:00:00Z",
    )
    _write_snapshot_with_sidecar(
        tmp_path,
        name="alpha.xml",
        fixture_name="schema_new.xml",
        profile="beta",
        fetched_at_utc="2026-05-31T20:00:00Z",
    )

    inspections = inspect_snapshot_directory(tmp_path)
    rendered = render_snapshot_list(inspections)

    assert inspections[0].relative_path == "alpha.xml"
    assert inspections[1].relative_path == "zeta.xml"
    assert "SNAPSHOT\tSTATUS\tTYPES\tPROFILE\tFETCHED_AT_UTC\tSHA256" in rendered
    assert "alpha.xml\tok\t2\tbeta\t2026-05-31T20:00:00Z" in rendered
    assert "zeta.xml\tok\t2\tv1.0\t2026-05-30T20:00:00Z" in rendered


def test_snapshot_validation_reports_missing_sidecar(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "orphan.xml"
    shutil.copyfile(FIXTURES_DIR / "schema_old.xml", snapshot_path)

    inspections = inspect_snapshot_directory(tmp_path)
    rendered = render_snapshot_validation(inspections)

    assert inspections[0].status == "invalid"
    assert rendered == f"ERROR\torphan.xml\tmissing sidecar: {snapshot_path}.json"


def test_load_snapshot_bundle_rejects_sha_mismatch(tmp_path: Path) -> None:
    snapshot_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="snapshot.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T20:00:00Z",
    )
    sidecar_path = sidecar_path_for_snapshot(snapshot_path)
    payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    payload["sha256"] = "0" * 64
    sidecar_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    try:
        load_snapshot_bundle(snapshot_path)
    except SnapshotValidationError as exc:
        assert "sidecar sha256 does not match snapshot content" in str(exc)
    else:
        raise AssertionError("expected load_snapshot_bundle to reject mismatched sha256")
