from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .diff import diff_snapshots
from .report import build_summary_report
from .snapshots import SnapshotValidationError, load_snapshot_bundle
from .source_compare import (
    build_source_comparison,
    render_source_comparison_json,
    render_source_comparison_markdown,
)
from .versioning import render_version_comparison_json, render_version_comparison_markdown
from .watchlists import (
    load_watchlist,
    match_watchlist,
    render_watchlist_json_report,
    render_watchlist_markdown_report,
)


MANIFEST_FIELDS = (
    "manifest_type",
    "workflow",
    "public_snapshot",
    "authenticated_snapshot",
    "watchlist",
    "allow_profile_mismatch",
    "outputs",
)

_WORKFLOW_NAME = "compare_public_authenticated"

_BASE_OUTPUT_KEYS = (
    "source_comparison_json",
    "source_comparison_markdown",
    "version_comparison_json",
    "version_comparison_markdown",
    "summary_json",
    "summary_markdown",
)

_BASE_OUTPUT_FILENAMES = {
    "source_comparison_json": "source-comparison.json",
    "source_comparison_markdown": "source-comparison.md",
    "version_comparison_json": "version-comparison.json",
    "version_comparison_markdown": "version-comparison.md",
    "summary_json": "summary.json",
    "summary_markdown": "summary.md",
}

_WATCHLIST_OUTPUT_KEYS = (
    "watchlist_json",
    "watchlist_markdown",
)

_WATCHLIST_OUTPUT_FILENAMES = {
    "watchlist_json": "watchlist.json",
    "watchlist_markdown": "watchlist.md",
}


@dataclass(frozen=True)
class WorkflowBundle:
    workflow: str
    public_snapshot: Path
    authenticated_snapshot: Path
    watchlist: Path | None
    allow_profile_mismatch: bool
    output_dir: Path
    outputs: dict[str, Path]


def build_compare_public_auth_bundle(
    public_snapshot_path: str | Path,
    authenticated_snapshot_path: str | Path,
    out_dir: str | Path,
    *,
    watchlist_path: str | Path | None = None,
    allow_profile_mismatch: bool = False,
    overwrite: bool = False,
) -> WorkflowBundle:
    """
    Orchestrate existing primitives to produce a deterministic local evidence bundle.
    No network access, no token or environment variable access.
    """
    pub = Path(public_snapshot_path)
    auth = Path(authenticated_snapshot_path)
    out = Path(out_dir)
    wl_path = Path(watchlist_path) if watchlist_path is not None else None

    # Step 1: Validate and create output directory
    if out.exists() and not out.is_dir():
        raise SnapshotValidationError(f"Output path exists but is not a directory: {out}")
    if not out.exists():
        if not out.parent.is_dir():
            raise SnapshotValidationError(f"Output parent directory does not exist: {out.parent}")
        out.mkdir()

    # Step 2: Compute planned output filenames and check for conflicts
    planned_filenames = dict(_BASE_OUTPUT_FILENAMES)
    if wl_path is not None:
        planned_filenames.update(_WATCHLIST_OUTPUT_FILENAMES)

    if not overwrite:
        existing = [name for name in planned_filenames.values() if (out / name).exists()]
        if existing:
            raise SnapshotValidationError(
                f"Output file(s) already exist (use --overwrite to overwrite): "
                + ", ".join(existing)
            )

    # Step 3: Build all content in memory before any file writes
    source_cmp = build_source_comparison(pub, auth, allow_profile_mismatch=allow_profile_mismatch)
    src_json = render_source_comparison_json(source_cmp)
    src_md = render_source_comparison_markdown(source_cmp)

    ver_cmp = source_cmp.version_comparison
    ver_json = render_version_comparison_json(ver_cmp)
    ver_md = render_version_comparison_markdown(ver_cmp)

    sum_json = build_summary_report(pub, auth, output_format="json")
    sum_md = build_summary_report(pub, auth, output_format="markdown")

    wl_json: str | None = None
    wl_md: str | None = None
    if wl_path is not None:
        pub_bundle = load_snapshot_bundle(pub)
        auth_bundle = load_snapshot_bundle(auth)
        changes = diff_snapshots(pub_bundle.snapshot, auth_bundle.snapshot)
        watchlist = load_watchlist(wl_path)
        matching = match_watchlist(changes, watchlist)
        wl_json = render_watchlist_json_report(pub_bundle, auth_bundle, watchlist, wl_path, changes, matching)
        wl_md = render_watchlist_markdown_report(pub_bundle, auth_bundle, watchlist, wl_path, changes, matching)

    # Build outputs dict (relative filenames → absolute paths for return value)
    output_paths: dict[str, Path] = {key: out / fname for key, fname in planned_filenames.items()}

    # Build manifest
    manifest_outputs = {key: fname for key, fname in planned_filenames.items()}
    bundle = WorkflowBundle(
        workflow=_WORKFLOW_NAME,
        public_snapshot=pub,
        authenticated_snapshot=auth,
        watchlist=wl_path,
        allow_profile_mismatch=allow_profile_mismatch,
        output_dir=out,
        outputs=output_paths,
    )
    manifest_str = render_manifest_json(bundle, manifest_outputs)

    # Step 4: Write all files atomically
    _write_text_file_atomic(out / "source-comparison.json", src_json + "\n")
    _write_text_file_atomic(out / "source-comparison.md", src_md + "\n")
    _write_text_file_atomic(out / "version-comparison.json", ver_json + "\n")
    _write_text_file_atomic(out / "version-comparison.md", ver_md + "\n")
    _write_text_file_atomic(out / "summary.json", sum_json + "\n")
    _write_text_file_atomic(out / "summary.md", sum_md + "\n")
    if wl_json is not None and wl_md is not None:
        _write_text_file_atomic(out / "watchlist.json", wl_json + "\n")
        _write_text_file_atomic(out / "watchlist.md", wl_md + "\n")
    _write_text_file_atomic(out / "manifest.json", manifest_str + "\n")

    return bundle


def render_manifest_json(bundle: WorkflowBundle, manifest_outputs: dict[str, str]) -> str:
    """Return deterministic manifest JSON string. No I/O."""
    payload = {
        "manifest_type": "workflow_bundle",
        "workflow": bundle.workflow,
        "public_snapshot": str(bundle.public_snapshot),
        "authenticated_snapshot": str(bundle.authenticated_snapshot),
        "watchlist": str(bundle.watchlist) if bundle.watchlist is not None else None,
        "allow_profile_mismatch": bundle.allow_profile_mismatch,
        "outputs": manifest_outputs,
    }
    approved_payload = {field: payload[field] for field in MANIFEST_FIELDS}
    return json.dumps(approved_payload, indent=2)


def _write_text_file_atomic(path: Path, content: str) -> None:
    temp_path: str | None = None
    try:
        existing_mode = path.stat().st_mode if path.exists() else None
        fd, temp_path = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        if existing_mode is not None:
            os.chmod(temp_path, existing_mode)
        os.replace(temp_path, path)
    except OSError as exc:
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        raise SnapshotValidationError(f"Failed to write file: {path}.") from exc
