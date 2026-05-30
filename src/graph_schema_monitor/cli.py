from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from .diff import changes_to_json, diff_snapshots, render_changes_text
from .parser import parse_csdl_file


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="graph-schema-monitor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect one type in a snapshot")
    inspect_parser.add_argument("--snapshot", required=True, help="Path to local CSDL/XML snapshot")
    inspect_parser.add_argument("--type", required=True, dest="type_name", help="Fully-qualified type name")

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


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "inspect":
        return _inspect(args)
    if args.command == "diff":
        return _diff(args)

    parser.print_help()
    return 2
