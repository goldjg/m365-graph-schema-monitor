from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from graph_schema_monitor.snapshots import SnapshotValidationError, sidecar_path_for_snapshot
from graph_schema_monitor.versioning import (
    JSON_VERSION_COMPARISON_REPORT_FIELDS,
    VersionComparison,
    build_version_comparison,
    classify_version_comparison,
    render_version_comparison_json,
    render_version_comparison_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "tests" / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_snapshot_with_sidecar(
    tmp_path: Path,
    *,
    name: str,
    fixture_name: str,
    profile: str,
    fetched_at_utc: str,
    x_ms_schema_version: str | None = "2026-05-30",
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
        "x_ms_schema_version": x_ms_schema_version,
    }
    sidecar_path_for_snapshot(snapshot_path).write_text(
        json.dumps(sidecar_payload, indent=2), encoding="utf-8"
    )
    return snapshot_path


def _make_comparison_same(tmp_path: Path) -> VersionComparison:
    """Return a VersionComparison where old == new (all booleans False)."""
    old_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="old.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
        x_ms_schema_version="2026-05-01",
    )
    new_path = _write_snapshot_with_sidecar(
        tmp_path / "new",
        name="new.xml",
        fixture_name="schema_old.xml",  # same fixture → same sha256
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
        x_ms_schema_version="2026-05-01",
    )
    (tmp_path / "new").mkdir(exist_ok=True)
    new_path = _write_snapshot_with_sidecar(
        tmp_path / "new",
        name="new.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
        x_ms_schema_version="2026-05-01",
    )
    return build_version_comparison(old_path, new_path)


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(ROOT / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_path if not existing else f"{src_path}{os.pathsep}{existing}"
    return subprocess.run(
        [sys.executable, "-m", "graph_schema_monitor", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


# ---------------------------------------------------------------------------
# Group 1 — classify_version_comparison() (CA-2)
# ---------------------------------------------------------------------------

def test_classify_all_false() -> None:
    assert classify_version_comparison(
        schema_version_changed=False, sha256_changed=False, semantic_changes_present=False
    ) == "version_same_content_same_semantics_same"


def test_classify_semantic_only() -> None:
    assert classify_version_comparison(
        schema_version_changed=False, sha256_changed=False, semantic_changes_present=True
    ) == "version_same_content_same_semantics_changed"


def test_classify_content_only() -> None:
    assert classify_version_comparison(
        schema_version_changed=False, sha256_changed=True, semantic_changes_present=False
    ) == "version_same_content_changed_semantics_same"


def test_classify_content_and_semantic() -> None:
    assert classify_version_comparison(
        schema_version_changed=False, sha256_changed=True, semantic_changes_present=True
    ) == "version_same_content_changed_semantics_changed"


def test_classify_version_only() -> None:
    assert classify_version_comparison(
        schema_version_changed=True, sha256_changed=False, semantic_changes_present=False
    ) == "version_changed_content_same_semantics_same"


def test_classify_version_and_semantic() -> None:
    assert classify_version_comparison(
        schema_version_changed=True, sha256_changed=False, semantic_changes_present=True
    ) == "version_changed_content_same_semantics_changed"


def test_classify_version_and_content() -> None:
    assert classify_version_comparison(
        schema_version_changed=True, sha256_changed=True, semantic_changes_present=False
    ) == "version_changed_content_changed_semantics_same"


def test_classify_all_true() -> None:
    assert classify_version_comparison(
        schema_version_changed=True, sha256_changed=True, semantic_changes_present=True
    ) == "version_changed_content_changed_semantics_changed"


# ---------------------------------------------------------------------------
# Group 2 — build_version_comparison() provenance failures (CA-1)
# ---------------------------------------------------------------------------

def test_missing_old_sidecar_raises(tmp_path: Path) -> None:
    old_xml = tmp_path / "old.xml"
    shutil.copyfile(FIXTURES_DIR / "schema_old.xml", old_xml)
    # No sidecar written for old

    new_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="new.xml",
        fixture_name="schema_new.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T00:00:00Z",
    )
    with pytest.raises(SnapshotValidationError):
        build_version_comparison(old_xml, new_path)


def test_missing_new_sidecar_raises(tmp_path: Path) -> None:
    old_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="old.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
    )
    new_xml = tmp_path / "new.xml"
    shutil.copyfile(FIXTURES_DIR / "schema_new.xml", new_xml)
    # No sidecar written for new

    with pytest.raises(SnapshotValidationError):
        build_version_comparison(old_path, new_xml)


def test_missing_old_x_ms_schema_version_raises(tmp_path: Path) -> None:
    old_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="old.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
        x_ms_schema_version=None,
    )
    new_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="new.xml",
        fixture_name="schema_new.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T00:00:00Z",
    )
    with pytest.raises(SnapshotValidationError, match="x_ms_schema_version is required"):
        build_version_comparison(old_path, new_path)


def test_missing_new_x_ms_schema_version_raises(tmp_path: Path) -> None:
    old_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="old.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
    )
    new_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="new.xml",
        fixture_name="schema_new.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T00:00:00Z",
        x_ms_schema_version=None,
    )
    with pytest.raises(SnapshotValidationError, match="x_ms_schema_version is required"):
        build_version_comparison(old_path, new_path)


def test_null_old_x_ms_schema_version_raises(tmp_path: Path) -> None:
    # x_ms_schema_version=None produces null JSON → _require_optional_str returns None
    old_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="old.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
        x_ms_schema_version=None,
    )
    new_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="new.xml",
        fixture_name="schema_new.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T00:00:00Z",
    )
    with pytest.raises(SnapshotValidationError):
        build_version_comparison(old_path, new_path)


def test_null_new_x_ms_schema_version_raises(tmp_path: Path) -> None:
    old_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="old.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
    )
    new_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="new.xml",
        fixture_name="schema_new.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T00:00:00Z",
        x_ms_schema_version=None,
    )
    with pytest.raises(SnapshotValidationError):
        build_version_comparison(old_path, new_path)


def test_invalid_sha256_sidecar_raises(tmp_path: Path) -> None:
    """Proves load_snapshot_bundle() hash-check propagates as SnapshotValidationError."""
    old_xml = tmp_path / "old.xml"
    shutil.copyfile(FIXTURES_DIR / "schema_old.xml", old_xml)
    # Write sidecar with a sha256 that does NOT match the file content.
    bad_sidecar = {
        "profile": "v1.0",
        "source_url": "https://graph.microsoft.com/v1.0/$metadata",
        "fetched_at_utc": "2026-05-01T00:00:00Z",
        "status_code": 200,
        "content_type": "application/xml; charset=utf-8",
        "etag": '"etag-1"',
        "last_modified": "Fri, 30 May 2026 20:00:00 GMT",
        "sha256": "0" * 64,  # 64 zeros — will not match the actual file
        "x_ms_schema_version": "2026-05-01",
    }
    sidecar_path_for_snapshot(old_xml).write_text(json.dumps(bad_sidecar, indent=2), encoding="utf-8")

    new_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="new.xml",
        fixture_name="schema_new.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T00:00:00Z",
    )
    with pytest.raises(SnapshotValidationError, match="sha256"):
        build_version_comparison(old_xml, new_path)


# ---------------------------------------------------------------------------
# Group 3 — build_version_comparison() success cases
# ---------------------------------------------------------------------------

def test_no_changes_all_same(tmp_path: Path) -> None:
    sub = tmp_path / "new"
    sub.mkdir()
    old_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="old.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
        x_ms_schema_version="2026-05-01",
    )
    new_path = _write_snapshot_with_sidecar(
        sub,
        name="new.xml",
        fixture_name="schema_old.xml",  # same fixture → same content, same sha256
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
        x_ms_schema_version="2026-05-01",
    )
    comparison = build_version_comparison(old_path, new_path)
    assert comparison.schema_version_changed is False
    assert comparison.sha256_changed is False
    assert comparison.semantic_changes_present is False
    assert comparison.semantic_change_count == 0
    assert comparison.classification == "version_same_content_same_semantics_same"


def test_all_changes(tmp_path: Path) -> None:
    sub = tmp_path / "new"
    sub.mkdir()
    old_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="old.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
        x_ms_schema_version="2026-05-01",
    )
    new_path = _write_snapshot_with_sidecar(
        sub,
        name="new.xml",
        fixture_name="schema_new.xml",  # different fixture → different sha256 and content
        profile="v1.0",
        fetched_at_utc="2026-05-30T00:00:00Z",
        x_ms_schema_version="2026-05-30",
    )
    comparison = build_version_comparison(old_path, new_path)
    assert comparison.schema_version_changed is True
    assert comparison.sha256_changed is True
    assert comparison.semantic_changes_present is True
    assert comparison.semantic_change_count > 0
    assert comparison.classification == "version_changed_content_changed_semantics_changed"


# ---------------------------------------------------------------------------
# Group 4 — render_version_comparison_markdown()
# ---------------------------------------------------------------------------

def test_markdown_contains_required_sections(tmp_path: Path) -> None:
    sub = tmp_path / "new"
    sub.mkdir()
    old_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="old.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
    )
    new_path = _write_snapshot_with_sidecar(
        sub,
        name="new.xml",
        fixture_name="schema_new.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T00:00:00Z",
        x_ms_schema_version="2026-05-30",
    )
    comparison = build_version_comparison(old_path, new_path)
    md = render_version_comparison_markdown(comparison)
    assert "# Graph Schema Version Comparison" in md
    assert "## Snapshots" in md
    assert "## Provenance" in md
    assert "## Change Detection" in md
    assert "## Classification" in md


def test_markdown_contains_classification_string(tmp_path: Path) -> None:
    sub = tmp_path / "new"
    sub.mkdir()
    old_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="old.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
    )
    new_path = _write_snapshot_with_sidecar(
        sub,
        name="new.xml",
        fixture_name="schema_new.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T00:00:00Z",
        x_ms_schema_version="2026-05-30",
    )
    comparison = build_version_comparison(old_path, new_path)
    md = render_version_comparison_markdown(comparison)
    assert comparison.classification in md


# ---------------------------------------------------------------------------
# Group 5 — render_version_comparison_json() (CA-3)
# ---------------------------------------------------------------------------

def test_json_top_level_fields_in_order(tmp_path: Path) -> None:
    sub = tmp_path / "new"
    sub.mkdir()
    old_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="old.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
    )
    new_path = _write_snapshot_with_sidecar(
        sub,
        name="new.xml",
        fixture_name="schema_new.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T00:00:00Z",
        x_ms_schema_version="2026-05-30",
    )
    comparison = build_version_comparison(old_path, new_path)
    parsed = json.loads(render_version_comparison_json(comparison))
    assert list(parsed.keys()) == list(JSON_VERSION_COMPARISON_REPORT_FIELDS)


def test_json_report_type_field(tmp_path: Path) -> None:
    sub = tmp_path / "new"
    sub.mkdir()
    old_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="old.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
    )
    new_path = _write_snapshot_with_sidecar(
        sub,
        name="new.xml",
        fixture_name="schema_new.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T00:00:00Z",
        x_ms_schema_version="2026-05-30",
    )
    comparison = build_version_comparison(old_path, new_path)
    parsed = json.loads(render_version_comparison_json(comparison))
    assert parsed["report_type"] == "version_comparison"


# ---------------------------------------------------------------------------
# Group 6 — CLI tests
# ---------------------------------------------------------------------------

def test_cli_version_compare_markdown(tmp_path: Path) -> None:
    sub = tmp_path / "new"
    sub.mkdir()
    old_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="old.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
    )
    new_path = _write_snapshot_with_sidecar(
        sub,
        name="new.xml",
        fixture_name="schema_new.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T00:00:00Z",
        x_ms_schema_version="2026-05-30",
    )
    result = _run_cli("version", "compare", "--old", str(old_path), "--new", str(new_path))
    assert result.returncode == 0
    assert "# Graph Schema Version Comparison" in result.stdout


def test_cli_version_compare_json(tmp_path: Path) -> None:
    sub = tmp_path / "new"
    sub.mkdir()
    old_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="old.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
    )
    new_path = _write_snapshot_with_sidecar(
        sub,
        name="new.xml",
        fixture_name="schema_new.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T00:00:00Z",
        x_ms_schema_version="2026-05-30",
    )
    result = _run_cli("version", "compare", "--old", str(old_path), "--new", str(new_path), "--format", "json")
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert list(parsed.keys()) == list(JSON_VERSION_COMPARISON_REPORT_FIELDS)


def test_cli_version_compare_out(tmp_path: Path) -> None:
    sub = tmp_path / "new"
    sub.mkdir()
    old_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="old.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
    )
    new_path = _write_snapshot_with_sidecar(
        sub,
        name="new.xml",
        fixture_name="schema_new.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T00:00:00Z",
        x_ms_schema_version="2026-05-30",
    )
    out_file = tmp_path / "report.md"
    result = _run_cli(
        "version", "compare",
        "--old", str(old_path),
        "--new", str(new_path),
        "--out", str(out_file),
    )
    assert result.returncode == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "# Graph Schema Version Comparison" in content


def test_cli_version_compare_missing_sidecar_exits_2(tmp_path: Path) -> None:
    old_xml = tmp_path / "old.xml"
    shutil.copyfile(FIXTURES_DIR / "schema_old.xml", old_xml)
    # No sidecar for old

    sub = tmp_path / "new"
    sub.mkdir()
    new_path = _write_snapshot_with_sidecar(
        sub,
        name="new.xml",
        fixture_name="schema_new.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T00:00:00Z",
    )
    result = _run_cli("version", "compare", "--old", str(old_xml), "--new", str(new_path))
    assert result.returncode == 2


# ---------------------------------------------------------------------------
# Group 7 — no-network assertion (CA-4)
# ---------------------------------------------------------------------------

def test_version_compare_no_network(tmp_path: Path) -> None:
    sub = tmp_path / "new"
    sub.mkdir()
    old_path = _write_snapshot_with_sidecar(
        tmp_path,
        name="old.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-01T00:00:00Z",
    )
    new_path = _write_snapshot_with_sidecar(
        sub,
        name="new.xml",
        fixture_name="schema_new.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T00:00:00Z",
        x_ms_schema_version="2026-05-30",
    )

    original_socket = socket.socket

    def _no_network(*args: object, **kwargs: object) -> None:  # type: ignore[return]
        raise AssertionError("build_version_comparison() must not open network sockets")

    with patch("socket.socket", side_effect=_no_network):
        # Should complete without raising AssertionError or any network error
        comparison = build_version_comparison(old_path, new_path)

    assert comparison is not None
