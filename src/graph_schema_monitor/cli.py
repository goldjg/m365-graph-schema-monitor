from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Sequence

from .diff import changes_to_json, diff_snapshots, render_changes_text
from .fetcher import FetchError, fetch_snapshot
from .parser import parse_csdl_file
from .report import build_diff_report
from .snapshots import (
    SnapshotValidationError,
    has_snapshot_errors,
    inspect_snapshot_directory,
    render_snapshot_list,
    render_snapshot_validation,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="graph-schema-monitor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect one type in a snapshot")
    inspect_parser.add_argument("--snapshot", required=True, help="Path to local CSDL/XML snapshot")
    inspect_parser.add_argument("--type", required=True, dest="type_name", help="Fully-qualified type name")
    inspect_parser.set_defaults(handler=_inspect)

    diff_parser = subparsers.add_parser("diff", help="Diff two local snapshots")
    diff_parser.add_argument("--old", required=True, dest="old_snapshot", help="Path to old snapshot")
    diff_parser.add_argument("--new", required=True, dest="new_snapshot", help="Path to new snapshot")
    diff_parser.add_argument("--type", dest="type_name", help="Optional fully-qualified type name")
    diff_parser.add_argument(
        "--format",
        dest="output_format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    diff_parser.set_defaults(handler=_diff)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch a Graph metadata snapshot")
    fetch_parser.add_argument("--profile", required=True, help="Graph metadata profile: v1.0 or beta")
    fetch_parser.add_argument("--out", required=True, dest="output_path", help="Output path for XML snapshot")
    fetch_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files")
    fetch_parser.set_defaults(handler=_fetch)

    snapshots_parser = subparsers.add_parser("snapshots", help="Inventory local snapshots")
    snapshots_subparsers = snapshots_parser.add_subparsers(dest="snapshots_command", required=True)

    snapshots_list_parser = snapshots_subparsers.add_parser("list", help="List local snapshots and sidecars")
    snapshots_list_parser.add_argument("--dir", required=True, dest="directory", help="Snapshot directory")
    snapshots_list_parser.set_defaults(handler=_snapshots_list)

    snapshots_validate_parser = snapshots_subparsers.add_parser(
        "validate", help="Validate local snapshots against sidecars"
    )
    snapshots_validate_parser.add_argument("--dir", required=True, dest="directory", help="Snapshot directory")
    snapshots_validate_parser.set_defaults(handler=_snapshots_validate)

    report_parser = subparsers.add_parser("report", help="Render deterministic reports")
    report_subparsers = report_parser.add_subparsers(dest="report_command", required=True)

    report_diff_parser = report_subparsers.add_parser("diff", help="Render a diff report from local snapshots")
    report_diff_parser.add_argument("--old", required=True, dest="old_snapshot", help="Path to old snapshot")
    report_diff_parser.add_argument("--new", required=True, dest="new_snapshot", help="Path to new snapshot")
    report_diff_parser.add_argument(
        "--format",
        dest="output_format",
        choices=["markdown", "json"],
        default="markdown",
        help="Report output format",
    )
    report_diff_parser.add_argument("--out", dest="output_path", help="Optional output path for the rendered report")
    report_diff_parser.set_defaults(handler=_report_diff)

    return parser


def _inspect(args: argparse.Namespace) -> int:
    snapshot = parse_csdl_file(args.snapshot)
    type_info = snapshot.types.get(args.type_name)
    if type_info is None:
        print(f"Type not found: {args.type_name}", file=sys.stderr)
        return 2

    print(f"Type: {type_info.full_name} ({type_info.kind})")
    for property_name, property_info in type_info.properties.items():
        print(
            f"{property_name}\ttype={property_info.property_type}\t"
            f"nullable={str(property_info.nullable).lower()}\t"
            f"collection={str(property_info.is_collection).lower()}"
        )
    return 0


def _diff(args: argparse.Namespace) -> int:
    old_snapshot = parse_csdl_file(args.old_snapshot)
    new_snapshot = parse_csdl_file(args.new_snapshot)

    if args.type_name and args.type_name not in old_snapshot.types and args.type_name not in new_snapshot.types:
        print(f"Type not found in either snapshot: {args.type_name}", file=sys.stderr)
        return 2

    changes = diff_snapshots(old_snapshot, new_snapshot, type_name=args.type_name)
    if args.output_format == "json":
        print(json.dumps(changes_to_json(changes), indent=2, sort_keys=True))
    else:
        print(render_changes_text(changes))
    return 0


def _fetch(args: argparse.Namespace) -> int:
    result = fetch_snapshot(
        args.profile,
        args.output_path,
        overwrite=args.overwrite,
    )
    print(f"Fetched {result.source_url} -> {result.output_path}")
    print(f"Sidecar: {result.sidecar_path}")
    return 0


def _snapshots_list(args: argparse.Namespace) -> int:
    inspections = inspect_snapshot_directory(args.directory)
    print(render_snapshot_list(inspections))
    return 0


def _snapshots_validate(args: argparse.Namespace) -> int:
    inspections = inspect_snapshot_directory(args.directory)
    print(render_snapshot_validation(inspections))
    return 1 if has_snapshot_errors(inspections) else 0


def _report_diff(args: argparse.Namespace) -> int:
    report = build_diff_report(args.old_snapshot, args.new_snapshot, output_format=args.output_format)
    if args.output_path:
        _write_output_file(Path(args.output_path), report + "\n")
        return 0
    print(report)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        return args.handler(args)
    except (FetchError, SnapshotValidationError) as exc:
        print(str(exc), file=sys.stderr)
        return exc.exit_code


def _write_output_file(path: Path, content: str) -> None:
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
