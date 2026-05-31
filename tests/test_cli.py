from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from graph_schema_monitor import cli
from graph_schema_monitor.snapshots import sidecar_path_for_snapshot


ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = ROOT / "tests" / "fixtures"


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


def test_cli_inspect_outputs_expected_type() -> None:
    result = _run_cli(
        "inspect",
        "--snapshot",
        str(FIXTURES_DIR / "schema_old.xml"),
        "--type",
        "microsoft.graph.conditionalAccessPolicy",
    )

    assert result.returncode == 0
    assert "Type: microsoft.graph.conditionalAccessPolicy (EntityType)" in result.stdout
    assert "displayName\ttype=Edm.String\tnullable=true\tcollection=false" in result.stdout


def test_cli_diff_json_outputs_template_id_addition() -> None:
    result = _run_cli(
        "diff",
        "--old",
        str(FIXTURES_DIR / "schema_old.xml"),
        "--new",
        str(FIXTURES_DIR / "schema_new.xml"),
        "--type",
        "microsoft.graph.conditionalAccessPolicy",
        "--format",
        "json",
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert any(item["change_type"] == "property_added" and item["property_name"] == "templateId" for item in payload)


def test_cli_snapshots_list_outputs_inventory(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_snapshot_with_sidecar(
        tmp_path,
        name="snapshot.xml",
        fixture_name="schema_old.xml",
        profile="v1.0",
        fetched_at_utc="2026-05-30T20:00:00Z",
    )

    exit_code = cli.main(["snapshots", "list", "--dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "SNAPSHOT\tSTATUS\tTYPES\tPROFILE\tFETCHED_AT_UTC\tSHA256" in captured.out
    assert "snapshot.xml\tok\t2\tv1.0\t2026-05-30T20:00:00Z" in captured.out


def test_cli_snapshots_validate_returns_nonzero_for_invalid_snapshot(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    shutil.copyfile(FIXTURES_DIR / "schema_old.xml", tmp_path / "snapshot.xml")

    exit_code = cli.main(["snapshots", "validate", "--dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "ERROR\tsnapshot.xml\tmissing sidecar:" in captured.out


def test_cli_report_diff_writes_to_stdout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
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

    exit_code = cli.main(["report", "diff", "--old", str(old_snapshot), "--new", str(new_snapshot)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "# Graph schema diff report" in captured.out
    assert "microsoft.graph.conditionalAccessPolicy.templateId" in captured.out


def test_cli_report_diff_writes_to_file(tmp_path: Path) -> None:
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
    output_path = tmp_path / "report.md"

    exit_code = cli.main(
        ["report", "diff", "--old", str(old_snapshot), "--new", str(new_snapshot), "--out", str(output_path)]
    )

    assert exit_code == 0
    assert output_path.exists()
    assert "# Graph schema diff report" in output_path.read_text(encoding="utf-8")
