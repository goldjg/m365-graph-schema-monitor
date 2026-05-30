from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


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
