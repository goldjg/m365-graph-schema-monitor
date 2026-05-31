from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
from pathlib import Path
from unittest.mock import patch

import pytest

from graph_schema_monitor.cli import main
from graph_schema_monitor.report import build_summary_report
from graph_schema_monitor.snapshots import SnapshotValidationError, load_snapshot_bundle, sidecar_path_for_snapshot
from graph_schema_monitor.source_compare import build_source_comparison, render_source_comparison_json
from graph_schema_monitor.versioning import build_version_comparison, render_version_comparison_json
from graph_schema_monitor.watchlists import (
    load_watchlist,
    match_watchlist,
    render_watchlist_json_report,
    render_watchlist_markdown_report,
)
from graph_schema_monitor.workflows import (
    MANIFEST_FIELDS,
    WorkflowBundle,
    build_compare_public_auth_bundle,
    render_manifest_json,
)
from graph_schema_monitor.diff import diff_snapshots


ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "tests" / "fixtures"

_XML_A_PATH = FIXTURES_DIR / "schema_old.xml"
_XML_B_PATH = FIXTURES_DIR / "schema_new.xml"
_WATCHLIST_PATH = FIXTURES_DIR / "watchlist_identity.json"


# ---------------------------------------------------------------------------
# Fixture helpers (adapted from test_source_compare.py)
# ---------------------------------------------------------------------------

def _make_standard_sidecar_fields(xml_path: Path, profile: str) -> dict:
    return {
        "profile": profile,
        "source_url": f"https://graph.microsoft.com/{profile}/$metadata",
        "fetched_at_utc": "2026-05-31T10:00:00Z",
        "status_code": 200,
        "content_type": "application/xml; charset=utf-8",
        "etag": '"etag-test"',
        "last_modified": "Sat, 31 May 2026 10:00:00 GMT",
        "sha256": hashlib.sha256(xml_path.read_bytes()).hexdigest(),
        "x_ms_schema_version": "1.4.592",
    }


def _make_xml(tmp_path: Path, name: str, source_fixture: Path) -> Path:
    dest = tmp_path / name
    shutil.copyfile(source_fixture, dest)
    return dest


def _write_public_sidecar(xml_path: Path, profile: str = "beta") -> None:
    payload = _make_standard_sidecar_fields(xml_path, profile)
    sidecar_path_for_snapshot(xml_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_auth_sidecar(
    xml_path: Path,
    profile: str = "beta",
    *,
    tenant_label: str | None = None,
) -> None:
    payload = _make_standard_sidecar_fields(xml_path, profile)
    payload["source_kind"] = "authenticated_graph_metadata"
    payload["auth_mode"] = "env_token"
    payload["tenant_label"] = tenant_label
    sidecar_path_for_snapshot(xml_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _make_pair(
    tmp_path: Path,
    *,
    pub_xml: Path = _XML_A_PATH,
    auth_xml: Path = _XML_A_PATH,
    pub_profile: str = "beta",
    auth_profile: str = "beta",
) -> tuple[Path, Path]:
    pub = _make_xml(tmp_path, "pub.xml", pub_xml)
    auth = _make_xml(tmp_path, "auth.xml", auth_xml)
    _write_public_sidecar(pub, pub_profile)
    _write_auth_sidecar(auth, auth_profile)
    return pub, auth


_EXPECTED_BASE_FILENAMES = frozenset({
    "source-comparison.json",
    "source-comparison.md",
    "version-comparison.json",
    "version-comparison.md",
    "summary.json",
    "summary.md",
    "manifest.json",
})

_EXPECTED_WATCHLIST_FILENAMES = frozenset({
    "watchlist.json",
    "watchlist.md",
})

_EXPECTED_ALL_FILENAMES = _EXPECTED_BASE_FILENAMES | _EXPECTED_WATCHLIST_FILENAMES


# ---------------------------------------------------------------------------
# CA-1: Workflow output set
# ---------------------------------------------------------------------------

class TestWorkflowOutputSet:
    def test_bundle_without_watchlist_writes_exactly_7_files(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        build_compare_public_auth_bundle(pub, auth, out_dir)
        files = {p.name for p in out_dir.iterdir()}
        assert len(files) == 7
        assert files == _EXPECTED_BASE_FILENAMES

    def test_bundle_with_watchlist_writes_exactly_9_files(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        build_compare_public_auth_bundle(pub, auth, out_dir, watchlist_path=_WATCHLIST_PATH)
        files = {p.name for p in out_dir.iterdir()}
        assert len(files) == 9
        assert files == _EXPECTED_ALL_FILENAMES

    def test_output_filenames_are_stable(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        build_compare_public_auth_bundle(pub, auth, out_dir)
        files = {p.name for p in out_dir.iterdir()}
        assert files == _EXPECTED_BASE_FILENAMES

    def test_output_dir_created_when_parent_exists(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "new-bundle-dir"
        assert not out_dir.exists()
        build_compare_public_auth_bundle(pub, auth, out_dir)
        assert out_dir.is_dir()

    def test_fails_if_out_dir_parent_does_not_exist(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "no-parent" / "bundle"
        with pytest.raises(SnapshotValidationError, match="parent directory"):
            build_compare_public_auth_bundle(pub, auth, out_dir)

    def test_fails_if_out_dir_is_a_file(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "not-a-dir"
        out_dir.write_text("not a directory")
        with pytest.raises(SnapshotValidationError, match="not a directory"):
            build_compare_public_auth_bundle(pub, auth, out_dir)


# ---------------------------------------------------------------------------
# CA-2: Manifest schema stability
# ---------------------------------------------------------------------------

class TestManifest:
    def _load_manifest(self, out_dir: Path) -> dict:
        return json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))

    def test_manifest_has_exact_approved_field_order(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        build_compare_public_auth_bundle(pub, auth, out_dir)
        data = self._load_manifest(out_dir)
        assert list(data.keys()) == list(MANIFEST_FIELDS)

    def test_manifest_output_values_are_relative_filenames(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        build_compare_public_auth_bundle(pub, auth, out_dir)
        data = self._load_manifest(out_dir)
        for value in data["outputs"].values():
            assert "/" not in value and "\\" not in value

    def test_manifest_watchlist_null_when_omitted(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        build_compare_public_auth_bundle(pub, auth, out_dir)
        data = self._load_manifest(out_dir)
        assert data["watchlist"] is None

    def test_manifest_includes_watchlist_path_when_supplied(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        build_compare_public_auth_bundle(pub, auth, out_dir, watchlist_path=_WATCHLIST_PATH)
        data = self._load_manifest(out_dir)
        assert data["watchlist"] == str(_WATCHLIST_PATH)

    def test_manifest_output_keys_match_generated_files(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        build_compare_public_auth_bundle(pub, auth, out_dir)
        data = self._load_manifest(out_dir)
        generated_files = {p.name for p in out_dir.iterdir() if p.name != "manifest.json"}
        manifest_files = set(data["outputs"].values())
        assert manifest_files == generated_files

    def test_manifest_output_keys_with_watchlist(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        build_compare_public_auth_bundle(pub, auth, out_dir, watchlist_path=_WATCHLIST_PATH)
        data = self._load_manifest(out_dir)
        assert "watchlist_json" in data["outputs"]
        assert "watchlist_markdown" in data["outputs"]
        assert data["outputs"]["watchlist_json"] == "watchlist.json"
        assert data["outputs"]["watchlist_markdown"] == "watchlist.md"

    def test_manifest_no_watchlist_omits_watchlist_keys(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        build_compare_public_auth_bundle(pub, auth, out_dir)
        data = self._load_manifest(out_dir)
        assert "watchlist_json" not in data["outputs"]
        assert "watchlist_markdown" not in data["outputs"]


# ---------------------------------------------------------------------------
# CA-3: Atomic / no-partial-write behaviour
# ---------------------------------------------------------------------------

class TestAtomicWrite:
    def test_existing_planned_output_without_overwrite_fails(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        out_dir.mkdir()
        (out_dir / "summary.json").write_text("existing")
        with pytest.raises(SnapshotValidationError, match="already exist"):
            build_compare_public_auth_bundle(pub, auth, out_dir)
        # No new files should have been written (only the pre-existing one)
        files = {p.name for p in out_dir.iterdir()}
        assert files == {"summary.json"}

    def test_existing_planned_output_with_overwrite_succeeds(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        out_dir.mkdir()
        (out_dir / "summary.json").write_text("existing")
        build_compare_public_auth_bundle(pub, auth, out_dir, overwrite=True)
        files = {p.name for p in out_dir.iterdir()}
        assert files == _EXPECTED_BASE_FILENAMES
        # Overwritten file should have been replaced
        assert (out_dir / "summary.json").read_text() != "existing"

    def test_render_failure_before_write_leaves_no_outputs(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        out_dir.mkdir()
        with patch(
            "graph_schema_monitor.workflows.build_source_comparison",
            side_effect=SnapshotValidationError("simulated failure"),
        ):
            with pytest.raises(SnapshotValidationError, match="simulated failure"):
                build_compare_public_auth_bundle(pub, auth, out_dir)
        # No output files should exist
        files = list(out_dir.iterdir())
        assert files == []


# ---------------------------------------------------------------------------
# CA-4: Primitive reuse
# ---------------------------------------------------------------------------

class TestPrimitiveReuse:
    def test_source_comparison_json_matches_direct_renderer(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        build_compare_public_auth_bundle(pub, auth, out_dir)
        written = (out_dir / "source-comparison.json").read_text(encoding="utf-8").strip()
        expected = render_source_comparison_json(build_source_comparison(pub, auth))
        assert written == expected

    def test_version_comparison_json_matches_direct_renderer(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        build_compare_public_auth_bundle(pub, auth, out_dir)
        written = (out_dir / "version-comparison.json").read_text(encoding="utf-8").strip()
        expected = render_version_comparison_json(build_version_comparison(pub, auth))
        assert written == expected

    def test_summary_json_matches_direct_build_summary_report(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        build_compare_public_auth_bundle(pub, auth, out_dir)
        written = (out_dir / "summary.json").read_text(encoding="utf-8").strip()
        expected = build_summary_report(pub, auth, output_format="json")
        assert written == expected

    def test_watchlist_json_matches_direct_renderer(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        build_compare_public_auth_bundle(pub, auth, out_dir, watchlist_path=_WATCHLIST_PATH)
        written = (out_dir / "watchlist.json").read_text(encoding="utf-8").strip()

        pub_bundle = load_snapshot_bundle(pub)
        auth_bundle = load_snapshot_bundle(auth)
        changes = diff_snapshots(pub_bundle.snapshot, auth_bundle.snapshot)
        watchlist = load_watchlist(_WATCHLIST_PATH)
        matching = match_watchlist(changes, watchlist)
        expected = render_watchlist_json_report(
            pub_bundle, auth_bundle, watchlist, _WATCHLIST_PATH, changes, matching
        )
        assert written == expected


# ---------------------------------------------------------------------------
# CA-5: Local-only / no-auth behaviour
# ---------------------------------------------------------------------------

class TestLocalOnly:
    def test_no_network_call_made(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"

        original_connect = socket.socket.connect

        def fail_connect(self, address):
            raise OSError("Network access forbidden in workflow tests")

        with patch.object(socket.socket, "connect", fail_connect):
            build_compare_public_auth_bundle(pub, auth, out_dir)
        assert out_dir.is_dir()

    def test_no_env_var_read(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"

        original_get = os.environ.get

        def fail_get(key, *args, **kwargs):
            raise OSError(f"os.environ.get({key!r}) called unexpectedly")

        with patch.object(os.environ, "get", fail_get):
            build_compare_public_auth_bundle(pub, auth, out_dir)
        assert out_dir.is_dir()

    def test_fetch_functions_not_called(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"

        def fail_fetch(*args, **kwargs):
            raise AssertionError("fetch_snapshot must not be called by workflow")

        def fail_fetch_auth(*args, **kwargs):
            raise AssertionError("fetch_authenticated_snapshot must not be called by workflow")

        with patch("graph_schema_monitor.fetcher.fetch_snapshot", side_effect=fail_fetch):
            with patch("graph_schema_monitor.fetcher.fetch_authenticated_snapshot", side_effect=fail_fetch_auth):
                build_compare_public_auth_bundle(pub, auth, out_dir)
        assert out_dir.is_dir()


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCLI:
    def test_workflow_compare_public_auth_success_without_watchlist(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        exit_code = main([
            "workflow", "compare-public-auth",
            "--public", str(pub),
            "--authenticated", str(auth),
            "--out-dir", str(out_dir),
        ])
        assert exit_code == 0
        assert {p.name for p in out_dir.iterdir()} == _EXPECTED_BASE_FILENAMES

    def test_workflow_compare_public_auth_success_with_watchlist(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        exit_code = main([
            "workflow", "compare-public-auth",
            "--public", str(pub),
            "--authenticated", str(auth),
            "--out-dir", str(out_dir),
            "--watchlist", str(_WATCHLIST_PATH),
        ])
        assert exit_code == 0
        assert {p.name for p in out_dir.iterdir()} == _EXPECTED_ALL_FILENAMES

    def test_workflow_compare_public_auth_overwrite(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_dir = tmp_path / "bundle"
        out_dir.mkdir()
        (out_dir / "summary.json").write_text("old-content")
        exit_code = main([
            "workflow", "compare-public-auth",
            "--public", str(pub),
            "--authenticated", str(auth),
            "--out-dir", str(out_dir),
            "--overwrite",
        ])
        assert exit_code == 0
        assert (out_dir / "summary.json").read_text() != "old-content"

    def test_missing_required_args_fail(self, tmp_path, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["workflow", "compare-public-auth", "--authenticated", "x.xml", "--out-dir", "/tmp"])
        assert exc_info.value.code != 0

    def test_profile_mismatch_failure_propagates_exit_2(self, tmp_path):
        pub, auth = _make_pair(tmp_path, pub_profile="v1.0", auth_profile="beta")
        out_dir = tmp_path / "bundle"
        exit_code = main([
            "workflow", "compare-public-auth",
            "--public", str(pub),
            "--authenticated", str(auth),
            "--out-dir", str(out_dir),
        ])
        assert exit_code == 2

    def test_allow_profile_mismatch_succeeds_with_warning(self, tmp_path):
        pub, auth = _make_pair(tmp_path, pub_profile="v1.0", auth_profile="beta")
        out_dir = tmp_path / "bundle"
        exit_code = main([
            "workflow", "compare-public-auth",
            "--public", str(pub),
            "--authenticated", str(auth),
            "--out-dir", str(out_dir),
            "--allow-profile-mismatch",
        ])
        assert exit_code == 0
        data = json.loads((out_dir / "source-comparison.json").read_text(encoding="utf-8"))
        assert data["profile_mismatch"] is True
