from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from graph_schema_monitor.snapshots import (
    SnapshotValidationError,
    has_snapshot_errors,
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
        profile="beta",
        fetched_at_utc="2026-05-31T20:00:00Z",
    )
    _write_snapshot_with_sidecar(
        tmp_path,
        name="alpha.xml",
        fixture_name="schema_new.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T20:00:00Z",
    )
    _write_snapshot_with_sidecar(
        tmp_path,
        name="middle.xml",
        fixture_name="schema_new.xml",
        profile="beta",
        fetched_at_utc="2026-05-29T20:00:00Z",
    )

    inspections = inspect_snapshot_directory(tmp_path)
    rendered = render_snapshot_list(inspections)

    assert [inspection.relative_path for inspection in inspections] == [
        "middle.xml",
        "zeta.xml",
        "alpha.xml",
    ]
    assert "SNAPSHOT\tSTATUS\tTYPES\tPROFILE\tFETCHED_AT_UTC\tSHA256" in rendered
    assert "middle.xml\tok\t2\tbeta\t2026-05-29T20:00:00Z" in rendered
    assert "zeta.xml\tok\t2\tbeta\t2026-05-31T20:00:00Z" in rendered
    assert "alpha.xml\tok\t2\tv1.0\t2026-05-30T20:00:00Z" in rendered


def test_snapshot_validation_reports_missing_sidecar(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "orphan.xml"
    shutil.copyfile(FIXTURES_DIR / "schema_old.xml", snapshot_path)

    inspections = inspect_snapshot_directory(tmp_path)
    rendered = render_snapshot_validation(inspections)

    assert inspections[0].status == "invalid"
    assert rendered == f"ERROR\torphan.xml\tmissing sidecar: {snapshot_path}.json"


def test_snapshot_list_reports_missing_sidecar_as_warning(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "orphan.xml"
    shutil.copyfile(FIXTURES_DIR / "schema_old.xml", snapshot_path)

    inspections = inspect_snapshot_directory(tmp_path, missing_sidecar_is_error=False)
    rendered = render_snapshot_list(inspections)

    assert inspections[0].status == "ok"
    assert inspections[0].inventory_status == "warning"
    assert rendered == "SNAPSHOT\tSTATUS\tTYPES\tPROFILE\tFETCHED_AT_UTC\tSHA256\norphan.xml\twarning\t2\t\t\t"


def test_snapshot_validation_warns_on_extra_sidecar_fields(tmp_path: Path) -> None:
    snapshot_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="snapshot.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T20:00:00Z",
    )
    sidecar_path = sidecar_path_for_snapshot(snapshot_path)
    payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    reordered_payload = {"unexpected": "value", "sha256": payload["sha256"], **payload}
    sidecar_path.write_text(json.dumps(reordered_payload, indent=2), encoding="utf-8")

    inspections = inspect_snapshot_directory(tmp_path)
    rendered = render_snapshot_validation(inspections)

    assert not has_snapshot_errors(inspections)
    assert inspections[0].status == "ok"
    assert "WARNING\tsnapshot.xml\textra sidecar field(s) ignored: unexpected" in rendered
    assert "OK\tsnapshot.xml" in rendered


def test_snapshot_validation_detects_orphan_sidecar(tmp_path: Path) -> None:
    orphan_sidecar = tmp_path / "orphan.xml.json"
    orphan_sidecar.write_text("{}", encoding="utf-8")

    inspections = inspect_snapshot_directory(tmp_path)
    rendered = render_snapshot_validation(inspections)

    assert [inspection.relative_path for inspection in inspections] == ["orphan.xml.json"]
    assert rendered == f"ERROR\torphan.xml.json\torphan sidecar: {orphan_sidecar}"


def test_snapshot_validation_detects_duplicate_sidecar_metadata_tuple(tmp_path: Path) -> None:
    _write_snapshot_with_sidecar(
        tmp_path,
        name="first.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T20:00:00Z",
    )
    _write_snapshot_with_sidecar(
        tmp_path,
        name="second.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T20:00:00Z",
    )

    inspections = inspect_snapshot_directory(tmp_path)
    rendered = render_snapshot_validation(inspections)

    assert has_snapshot_errors(inspections)
    assert rendered.count("duplicate snapshot metadata tuple") == 2


def test_snapshot_renderers_handle_empty_directory(tmp_path: Path) -> None:
    inspections = inspect_snapshot_directory(tmp_path)

    assert inspections == []
    assert render_snapshot_list(inspections) == "No snapshot files found."
    assert render_snapshot_validation(inspections) == "No snapshot files found."


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


def test_load_snapshot_bundle_accepts_sidecar_keys_out_of_order(tmp_path: Path) -> None:
    snapshot_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="snapshot.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T20:00:00Z",
    )
    sidecar_path = sidecar_path_for_snapshot(snapshot_path)
    payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    reordered_payload = {
        "sha256": payload["sha256"],
        "profile": payload["profile"],
        "content_type": payload["content_type"],
        "source_url": payload["source_url"],
        "fetched_at_utc": payload["fetched_at_utc"],
        "status_code": payload["status_code"],
        "etag": payload["etag"],
        "last_modified": payload["last_modified"],
        "x_ms_schema_version": payload["x_ms_schema_version"],
    }
    sidecar_path.write_text(json.dumps(reordered_payload, indent=2), encoding="utf-8")

    bundle = load_snapshot_bundle(snapshot_path)

    assert bundle.sidecar is not None
    assert bundle.sidecar.sha256 == payload["sha256"]


def test_snapshot_inventory_ignores_symlinked_candidates_outside_root(tmp_path: Path) -> None:
    outside_dir = tmp_path.parent / "outside-root"
    outside_dir.mkdir()
    outside_snapshot = _write_snapshot_with_sidecar(
        outside_dir,
        name="outside.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T20:00:00Z",
    )
    (tmp_path / "linked.xml").symlink_to(outside_snapshot)
    (tmp_path / "linked.xml.json").symlink_to(sidecar_path_for_snapshot(outside_snapshot))

    inspections = inspect_snapshot_directory(tmp_path)

    assert inspections == []
