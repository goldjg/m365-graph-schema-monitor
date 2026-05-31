from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from graph_schema_monitor.cli import main
from graph_schema_monitor.snapshots import SnapshotValidationError, sidecar_path_for_snapshot
from graph_schema_monitor.source_compare import (
    JSON_SOURCE_COMPARISON_FIELDS,
    SourceComparison,
    build_source_comparison,
    render_source_comparison_json,
    render_source_comparison_markdown,
)
from graph_schema_monitor.versioning import build_version_comparison


ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "tests" / "fixtures"

# XML content variants for testing — reuse existing fixture content
_XML_A_PATH = FIXTURES_DIR / "schema_old.xml"
_XML_B_PATH = FIXTURES_DIR / "schema_new.xml"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_standard_sidecar_fields(xml_path: Path, profile: str) -> dict:
    """Return the 9 standard sidecar fields for an XML path."""
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
    """Copy a fixture XML to tmp_path under the given name."""
    dest = tmp_path / name
    shutil.copyfile(source_fixture, dest)
    return dest


def _write_public_sidecar(xml_path: Path, profile: str, *, source_kind: str | None = None) -> None:
    """Write a public sidecar .xml.json adjacent to xml_path."""
    payload = _make_standard_sidecar_fields(xml_path, profile)
    if source_kind is not None:
        payload["source_kind"] = source_kind
    sidecar_path_for_snapshot(xml_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_auth_sidecar(
    xml_path: Path,
    profile: str,
    *,
    source_kind: str = "authenticated_graph_metadata",
    auth_mode: str = "env_token",
    tenant_label: str | None = None,
    omit_source_kind: bool = False,
    omit_auth_mode: bool = False,
) -> None:
    """Write an authenticated sidecar .xml.json adjacent to xml_path."""
    payload = _make_standard_sidecar_fields(xml_path, profile)
    if not omit_source_kind:
        payload["source_kind"] = source_kind
    if not omit_auth_mode:
        payload["auth_mode"] = auth_mode
    payload["tenant_label"] = tenant_label
    sidecar_path_for_snapshot(xml_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _make_pair(
    tmp_path: Path,
    *,
    pub_xml: Path = _XML_A_PATH,
    auth_xml: Path = _XML_A_PATH,
    pub_profile: str = "beta",
    auth_profile: str = "beta",
    pub_source_kind: str | None = None,
    auth_tenant_label: str | None = None,
) -> tuple[Path, Path]:
    """Create a standard valid public+authenticated snapshot pair in tmp_path."""
    pub = _make_xml(tmp_path, "pub.xml", pub_xml)
    auth = _make_xml(tmp_path, "auth.xml", auth_xml)
    _write_public_sidecar(pub, pub_profile, source_kind=pub_source_kind)
    _write_auth_sidecar(auth, auth_profile, tenant_label=auth_tenant_label)
    return pub, auth


# ---------------------------------------------------------------------------
# CA-1: Source provenance validation
# ---------------------------------------------------------------------------

class TestPublicProvenance:
    def test_no_source_kind_accepted_as_public(self, tmp_path):
        pub, auth = _make_pair(tmp_path, pub_source_kind=None)
        result = build_source_comparison(pub, auth)
        assert result.public_source_kind == "public_graph_metadata"

    def test_explicit_public_source_kind_accepted(self, tmp_path):
        pub, auth = _make_pair(tmp_path, pub_source_kind="public_graph_metadata")
        result = build_source_comparison(pub, auth)
        assert result.public_source_kind == "public_graph_metadata"

    def test_auth_source_kind_on_public_rejected(self, tmp_path):
        pub = _make_xml(tmp_path, "pub.xml", _XML_A_PATH)
        auth = _make_xml(tmp_path, "auth.xml", _XML_A_PATH)
        _write_public_sidecar(pub, "beta", source_kind="authenticated_graph_metadata")
        _write_auth_sidecar(auth, "beta")
        with pytest.raises(SnapshotValidationError, match="authenticated source_kind"):
            build_source_comparison(pub, auth)

    def test_unknown_source_kind_on_public_rejected(self, tmp_path):
        pub = _make_xml(tmp_path, "pub.xml", _XML_A_PATH)
        auth = _make_xml(tmp_path, "auth.xml", _XML_A_PATH)
        _write_public_sidecar(pub, "beta", source_kind="something_else")
        _write_auth_sidecar(auth, "beta")
        with pytest.raises(SnapshotValidationError, match="unknown source_kind"):
            build_source_comparison(pub, auth)


class TestAuthProvenance:
    def test_valid_auth_accepted(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        result = build_source_comparison(pub, auth)
        assert result.authenticated_source_kind == "authenticated_graph_metadata"
        assert result.authenticated_auth_mode == "env_token"

    def test_missing_source_kind_rejected(self, tmp_path):
        pub = _make_xml(tmp_path, "pub.xml", _XML_A_PATH)
        auth = _make_xml(tmp_path, "auth.xml", _XML_A_PATH)
        _write_public_sidecar(pub, "beta")
        _write_auth_sidecar(auth, "beta", omit_source_kind=True)
        with pytest.raises(SnapshotValidationError, match="missing required source_kind"):
            build_source_comparison(pub, auth)

    def test_public_source_kind_on_auth_rejected(self, tmp_path):
        pub = _make_xml(tmp_path, "pub.xml", _XML_A_PATH)
        auth = _make_xml(tmp_path, "auth.xml", _XML_A_PATH)
        _write_public_sidecar(pub, "beta")
        _write_auth_sidecar(auth, "beta", source_kind="public_graph_metadata")
        with pytest.raises(SnapshotValidationError, match="unexpected source_kind"):
            build_source_comparison(pub, auth)

    def test_missing_auth_mode_rejected(self, tmp_path):
        pub = _make_xml(tmp_path, "pub.xml", _XML_A_PATH)
        auth = _make_xml(tmp_path, "auth.xml", _XML_A_PATH)
        _write_public_sidecar(pub, "beta")
        _write_auth_sidecar(auth, "beta", omit_auth_mode=True)
        with pytest.raises(SnapshotValidationError, match="missing required auth_mode"):
            build_source_comparison(pub, auth)

    def test_wrong_auth_mode_rejected(self, tmp_path):
        pub = _make_xml(tmp_path, "pub.xml", _XML_A_PATH)
        auth = _make_xml(tmp_path, "auth.xml", _XML_A_PATH)
        _write_public_sidecar(pub, "beta")
        _write_auth_sidecar(auth, "beta", auth_mode="client_credentials")
        with pytest.raises(SnapshotValidationError, match="unexpected auth_mode"):
            build_source_comparison(pub, auth)

    def test_tenant_label_string_accepted(self, tmp_path):
        pub, auth = _make_pair(tmp_path, auth_tenant_label="lab")
        result = build_source_comparison(pub, auth)
        assert result.authenticated_tenant_label == "lab"

    def test_tenant_label_null_accepted(self, tmp_path):
        pub, auth = _make_pair(tmp_path, auth_tenant_label=None)
        result = build_source_comparison(pub, auth)
        assert result.authenticated_tenant_label is None


# ---------------------------------------------------------------------------
# CA-2: Profile mismatch behaviour
# ---------------------------------------------------------------------------

class TestProfileHandling:
    def test_matching_profiles_succeeds(self, tmp_path):
        pub, auth = _make_pair(tmp_path, pub_profile="beta", auth_profile="beta")
        result = build_source_comparison(pub, auth)
        assert result.profile_mismatch is False
        assert result.warnings == ()

    def test_mismatched_profiles_fail_by_default(self, tmp_path):
        pub = _make_xml(tmp_path, "pub.xml", _XML_A_PATH)
        auth = _make_xml(tmp_path, "auth.xml", _XML_A_PATH)
        _write_public_sidecar(pub, "beta")
        _write_auth_sidecar(auth, "v1.0")
        with pytest.raises(SnapshotValidationError, match="profile mismatch"):
            build_source_comparison(pub, auth)

    def test_mismatched_profiles_allowed_with_flag(self, tmp_path):
        pub = _make_xml(tmp_path, "pub.xml", _XML_A_PATH)
        auth = _make_xml(tmp_path, "auth.xml", _XML_A_PATH)
        _write_public_sidecar(pub, "beta")
        _write_auth_sidecar(auth, "v1.0")
        result = build_source_comparison(pub, auth, allow_profile_mismatch=True)
        assert result.profile_mismatch is True

    def test_mismatched_profiles_with_flag_includes_warning(self, tmp_path):
        pub = _make_xml(tmp_path, "pub.xml", _XML_A_PATH)
        auth = _make_xml(tmp_path, "auth.xml", _XML_A_PATH)
        _write_public_sidecar(pub, "beta")
        _write_auth_sidecar(auth, "v1.0")
        result = build_source_comparison(pub, auth, allow_profile_mismatch=True)
        assert len(result.warnings) == 1
        assert "profile mismatch" in result.warnings[0].lower()


# ---------------------------------------------------------------------------
# CA-3: Version comparison reuse
# ---------------------------------------------------------------------------

class TestVersionComparisonReuse:
    def test_same_xml_same_classification(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        result = build_source_comparison(pub, auth)
        vc = result.version_comparison
        assert vc.classification == "version_same_content_same_semantics_same"
        assert vc.schema_version_changed is False
        assert vc.sha256_changed is False
        assert vc.semantic_changes_present is False

    def test_same_xml_matches_build_version_comparison(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        result = build_source_comparison(pub, auth)
        reference = build_version_comparison(pub, auth)
        assert result.version_comparison.classification == reference.classification
        assert result.version_comparison.sha256_changed == reference.sha256_changed
        assert result.version_comparison.semantic_change_count == reference.semantic_change_count

    def test_different_xml_semantic_count_matches(self, tmp_path):
        pub = _make_xml(tmp_path, "pub.xml", _XML_A_PATH)
        auth = _make_xml(tmp_path, "auth.xml", _XML_B_PATH)
        _write_public_sidecar(pub, "beta")
        _write_auth_sidecar(auth, "beta")
        result = build_source_comparison(pub, auth)
        reference = build_version_comparison(pub, auth)
        assert result.version_comparison.semantic_change_count == reference.semantic_change_count
        assert result.version_comparison.sha256_changed is True


# ---------------------------------------------------------------------------
# CA-4: JSON schema stability
# ---------------------------------------------------------------------------

class TestJsonSchemaStability:
    def test_json_has_exact_approved_fields(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        result = build_source_comparison(pub, auth)
        output = json.loads(render_source_comparison_json(result))
        assert set(output.keys()) == set(JSON_SOURCE_COMPARISON_FIELDS)

    def test_json_field_order_is_stable(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        result = build_source_comparison(pub, auth)
        output = json.loads(render_source_comparison_json(result))
        assert list(output.keys()) == list(JSON_SOURCE_COMPARISON_FIELDS)

    def test_json_report_type(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        result = build_source_comparison(pub, auth)
        output = json.loads(render_source_comparison_json(result))
        assert output["report_type"] == "source_comparison"
        assert output["comparison_kind"] == "public_vs_authenticated"

    def test_json_contains_no_token_fields(self, tmp_path):
        pub, auth = _make_pair(tmp_path, auth_tenant_label="lab")
        result = build_source_comparison(pub, auth)
        raw_json = render_source_comparison_json(result)
        output = json.loads(raw_json)
        forbidden = {"token", "bearer", "authorization", "secret", "credential", "tenant_id", "app_id", "user_id"}
        for key in output:
            assert key.lower() not in forbidden, f"Forbidden field in JSON output: {key!r}"
        # Check values too: tenant_label is "lab" (opaque display string), not an ID
        for key, val in output.items():
            if isinstance(val, str):
                assert "Bearer" not in val


# ---------------------------------------------------------------------------
# Markdown structure tests
# ---------------------------------------------------------------------------

class TestMarkdownOutput:
    def _render(self, tmp_path, **kwargs) -> str:
        pub, auth = _make_pair(tmp_path, **kwargs)
        result = build_source_comparison(pub, auth)
        return render_source_comparison_markdown(result)

    def test_title(self, tmp_path):
        md = self._render(tmp_path)
        assert "# Graph Schema Source Comparison" in md

    def test_required_sections(self, tmp_path):
        md = self._render(tmp_path)
        assert "## Sources" in md
        assert "## Profiles" in md
        assert "## Version and Content" in md
        assert "## Semantic Diff" in md
        assert "## Classification" in md
        assert "## Warnings" in md

    def test_no_warning_case(self, tmp_path):
        md = self._render(tmp_path)
        # Warnings section should end with None.
        assert "None." in md

    def test_warning_case_has_bullet(self, tmp_path):
        pub = _make_xml(tmp_path, "pub.xml", _XML_A_PATH)
        auth = _make_xml(tmp_path, "auth.xml", _XML_A_PATH)
        _write_public_sidecar(pub, "beta")
        _write_auth_sidecar(auth, "v1.0")
        result = build_source_comparison(pub, auth, allow_profile_mismatch=True)
        md = render_source_comparison_markdown(result)
        assert "## Warnings" in md
        # Should have at least one bullet point after Warnings
        after_warnings = md.split("## Warnings")[1]
        assert "- " in after_warnings

    def test_comparison_kind_in_output(self, tmp_path):
        md = self._render(tmp_path)
        assert "public_vs_authenticated" in md

    def test_auth_mode_in_output(self, tmp_path):
        md = self._render(tmp_path)
        assert "env_token" in md

    def test_tenant_label_none_shown(self, tmp_path):
        md = self._render(tmp_path, auth_tenant_label=None)
        assert "none" in md

    def test_tenant_label_value_shown(self, tmp_path):
        md = self._render(tmp_path, auth_tenant_label="lab")
        assert "lab" in md

    def test_classification_in_output(self, tmp_path):
        md = self._render(tmp_path)
        assert "version_same_content_same_semantics_same" in md


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

class TestCli:
    def _run(self, args: list[str]) -> tuple[int, str]:
        buf = StringIO()
        with patch("sys.stdout", buf):
            code = main(args)
        return code, buf.getvalue()

    def test_markdown_format(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        code, out = self._run([
            "version", "compare-sources",
            "--public", str(pub),
            "--authenticated", str(auth),
            "--format", "markdown",
        ])
        assert code == 0
        assert "# Graph Schema Source Comparison" in out

    def test_json_format(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        code, out = self._run([
            "version", "compare-sources",
            "--public", str(pub),
            "--authenticated", str(auth),
            "--format", "json",
        ])
        assert code == 0
        parsed = json.loads(out)
        assert parsed["report_type"] == "source_comparison"

    def test_default_format_is_markdown(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        code, out = self._run([
            "version", "compare-sources",
            "--public", str(pub),
            "--authenticated", str(auth),
        ])
        assert code == 0
        assert "# Graph Schema Source Comparison" in out

    def test_out_file(self, tmp_path):
        pub, auth = _make_pair(tmp_path)
        out_file = tmp_path / "report.md"
        code, _ = self._run([
            "version", "compare-sources",
            "--public", str(pub),
            "--authenticated", str(auth),
            "--out", str(out_file),
        ])
        assert code == 0
        assert out_file.exists()
        assert "# Graph Schema Source Comparison" in out_file.read_text(encoding="utf-8")

    def test_profile_mismatch_exits_2(self, tmp_path):
        pub = _make_xml(tmp_path, "pub.xml", _XML_A_PATH)
        auth = _make_xml(tmp_path, "auth.xml", _XML_A_PATH)
        _write_public_sidecar(pub, "beta")
        _write_auth_sidecar(auth, "v1.0")
        buf_err = StringIO()
        with patch("sys.stderr", buf_err):
            code = main([
                "version", "compare-sources",
                "--public", str(pub),
                "--authenticated", str(auth),
            ])
        assert code == 2

    def test_allow_profile_mismatch_exits_0(self, tmp_path):
        pub = _make_xml(tmp_path, "pub.xml", _XML_A_PATH)
        auth = _make_xml(tmp_path, "auth.xml", _XML_A_PATH)
        _write_public_sidecar(pub, "beta")
        _write_auth_sidecar(auth, "v1.0")
        code, out = self._run([
            "version", "compare-sources",
            "--public", str(pub),
            "--authenticated", str(auth),
            "--allow-profile-mismatch",
        ])
        assert code == 0
        assert "profile mismatch" in out.lower()

    def test_invalid_public_provenance_exits_2(self, tmp_path):
        pub = _make_xml(tmp_path, "pub.xml", _XML_A_PATH)
        auth = _make_xml(tmp_path, "auth.xml", _XML_A_PATH)
        _write_public_sidecar(pub, "beta", source_kind="authenticated_graph_metadata")
        _write_auth_sidecar(auth, "beta")
        buf_err = StringIO()
        with patch("sys.stderr", buf_err):
            code = main([
                "version", "compare-sources",
                "--public", str(pub),
                "--authenticated", str(auth),
            ])
        assert code == 2

    def test_invalid_auth_provenance_exits_2(self, tmp_path):
        pub = _make_xml(tmp_path, "pub.xml", _XML_A_PATH)
        auth = _make_xml(tmp_path, "auth.xml", _XML_A_PATH)
        _write_public_sidecar(pub, "beta")
        _write_auth_sidecar(auth, "beta", omit_source_kind=True)
        buf_err = StringIO()
        with patch("sys.stderr", buf_err):
            code = main([
                "version", "compare-sources",
                "--public", str(pub),
                "--authenticated", str(auth),
            ])
        assert code == 2


# ---------------------------------------------------------------------------
# CA-5: Local-only / no-auth tests
# ---------------------------------------------------------------------------

class TestLocalOnly:
    def test_succeeds_with_no_network(self, tmp_path, monkeypatch):
        """Blocking socket.create_connection must not affect compare-sources."""
        pub, auth = _make_pair(tmp_path)

        def _no_network(*args, **kwargs):
            raise OSError("network disabled in test")

        monkeypatch.setattr(socket, "create_connection", _no_network)
        result = build_source_comparison(pub, auth)
        assert result.comparison_kind == "public_vs_authenticated"

    def test_succeeds_with_env_disabled(self, tmp_path, monkeypatch):
        """Even if os.environ.get raises, compare-sources must still succeed."""
        pub, auth = _make_pair(tmp_path)

        original_get = os.environ.get

        def _raise_on_env(key, *args, **kwargs):
            raise RuntimeError(f"env access disabled in test: {key}")

        monkeypatch.setattr(os.environ, "get", _raise_on_env)
        result = build_source_comparison(pub, auth)
        assert result.comparison_kind == "public_vs_authenticated"

    def test_succeeds_even_if_fetch_snapshot_would_raise(self, tmp_path, monkeypatch):
        """fetch_snapshot must never be called by compare-sources."""
        pub, auth = _make_pair(tmp_path)
        import graph_schema_monitor.fetcher as fetcher_mod

        def _never_called(*args, **kwargs):
            raise AssertionError("fetch_snapshot must not be called by compare-sources")

        monkeypatch.setattr(fetcher_mod, "fetch_snapshot", _never_called)
        monkeypatch.setattr(fetcher_mod, "fetch_authenticated_snapshot", _never_called)
        result = build_source_comparison(pub, auth)
        assert result.comparison_kind == "public_vs_authenticated"
