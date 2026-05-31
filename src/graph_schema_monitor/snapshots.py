from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from .fetcher import ALLOWED_SIDECAR_FIELDS, _is_xml_content_type, resolve_profile_url
from .parser import SchemaSnapshot, parse_csdl_file


@dataclass(frozen=True)
class SnapshotSidecar:
    profile: str
    source_url: str
    fetched_at_utc: str
    status_code: int
    content_type: str | None
    etag: str | None
    last_modified: str | None
    sha256: str
    x_ms_schema_version: str | None


@dataclass(frozen=True)
class SnapshotBundle:
    snapshot_path: Path
    sidecar_path: Path
    snapshot: SchemaSnapshot
    sidecar: SnapshotSidecar | None


@dataclass(frozen=True)
class SnapshotInspection:
    relative_path: str
    snapshot_path: Path
    sidecar_path: Path
    type_count: int | None
    sidecar: SnapshotSidecar | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    @property
    def status(self) -> str:
        return "ok" if not self.errors else "invalid"


class SnapshotValidationError(Exception):
    exit_code = 2


def sidecar_path_for_snapshot(snapshot_path: str | Path) -> Path:
    return Path(f"{Path(snapshot_path)}.json")


def discover_snapshot_paths(directory: str | Path) -> tuple[Path, list[Path], list[Path]]:
    root = Path(directory)
    if not root.exists() or not root.is_dir():
        raise SnapshotValidationError(f"Snapshot directory does not exist: {root}")
    snapshot_candidates = (path for path in root.rglob("*.xml") if path.is_file())
    sidecar_candidates = (path for path in root.rglob("*.xml.json") if path.is_file())
    snapshots = sorted(snapshot_candidates, key=lambda path: path.relative_to(root).as_posix())
    sidecars = sorted(sidecar_candidates, key=lambda path: path.relative_to(root).as_posix())
    return root, snapshots, sidecars


def inspect_snapshot_directory(directory: str | Path) -> list[SnapshotInspection]:
    root, snapshots, sidecars = discover_snapshot_paths(directory)
    inspections = [inspect_snapshot_file(path, root=root) for path in snapshots]

    snapshot_paths = set(snapshots)
    for sidecar_path in sidecars:
        snapshot_path = sidecar_path.with_suffix("")
        if snapshot_path in snapshot_paths:
            continue
        inspections.append(
            SnapshotInspection(
                relative_path=sidecar_path.relative_to(root).as_posix(),
                snapshot_path=snapshot_path,
                sidecar_path=sidecar_path,
                type_count=None,
                sidecar=None,
                errors=(f"orphan sidecar: {sidecar_path}",),
            )
        )

    inspections = _apply_duplicate_errors(inspections)
    return sorted(inspections, key=_inspection_sort_key)


def inspect_snapshot_file(snapshot_path: str | Path, *, root: Path | None = None) -> SnapshotInspection:
    path = Path(snapshot_path)
    display_path = path.relative_to(root).as_posix() if root is not None else str(path)
    sidecar_path = sidecar_path_for_snapshot(path)
    errors: list[str] = []
    warnings: list[str] = []
    type_count: int | None = None
    sidecar: SnapshotSidecar | None = None

    try:
        snapshot = parse_csdl_file(path)
        type_count = len(snapshot.types)
    except Exception as exc:
        errors.append(f"snapshot parse failed: {exc}")

    if not sidecar_path.exists() or not sidecar_path.is_file():
        errors.append(f"missing sidecar: {sidecar_path}")
    else:
        try:
            sidecar, sidecar_warnings = _load_snapshot_sidecar_result(path, sidecar_path=sidecar_path)
            warnings.extend(sidecar_warnings)
        except SnapshotValidationError as exc:
            errors.append(str(exc))

    return SnapshotInspection(
        relative_path=display_path,
        snapshot_path=path,
        sidecar_path=sidecar_path,
        type_count=type_count,
        sidecar=sidecar,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def load_snapshot_bundle(snapshot_path: str | Path, *, allow_missing_sidecar: bool = False) -> SnapshotBundle:
    path = Path(snapshot_path)
    sidecar_path = sidecar_path_for_snapshot(path)
    if not sidecar_path.exists() or not sidecar_path.is_file():
        if allow_missing_sidecar:
            sidecar = None
        else:
            raise SnapshotValidationError(f"Missing sidecar for snapshot: {path}")
    else:
        sidecar = load_snapshot_sidecar(path, sidecar_path=sidecar_path)

    try:
        snapshot = parse_csdl_file(path)
    except Exception as exc:
        raise SnapshotValidationError(f"Failed to parse snapshot XML: {path}") from exc

    return SnapshotBundle(
        snapshot_path=path,
        sidecar_path=sidecar_path,
        snapshot=snapshot,
        sidecar=sidecar,
    )


def render_snapshot_list(inspections: list[SnapshotInspection]) -> str:
    if not inspections:
        return "No snapshot files found."

    lines = ["SNAPSHOT\tSTATUS\tTYPES\tPROFILE\tFETCHED_AT_UTC\tSHA256"]
    for inspection in inspections:
        sidecar = inspection.sidecar
        lines.append(
            "\t".join(
                [
                    inspection.relative_path,
                    inspection.status,
                    "" if inspection.type_count is None else str(inspection.type_count),
                    "" if sidecar is None else sidecar.profile,
                    "" if sidecar is None else sidecar.fetched_at_utc,
                    "" if sidecar is None else sidecar.sha256,
                ]
            )
        )
    return "\n".join(lines)


def render_snapshot_validation(inspections: list[SnapshotInspection]) -> str:
    if not inspections:
        return "No snapshot files found."

    lines: list[str] = []
    for inspection in inspections:
        for warning in inspection.warnings:
            lines.append(f"WARNING\t{inspection.relative_path}\t{warning}")
        if not inspection.errors:
            lines.append(f"OK\t{inspection.relative_path}")
            continue
        for error in inspection.errors:
            lines.append(f"ERROR\t{inspection.relative_path}\t{error}")
    return "\n".join(lines)


def has_snapshot_errors(inspections: list[SnapshotInspection]) -> bool:
    return any(inspection.errors for inspection in inspections)


def load_snapshot_sidecar(snapshot_path: str | Path, *, sidecar_path: str | Path | None = None) -> SnapshotSidecar:
    sidecar, _warnings = _load_snapshot_sidecar_result(snapshot_path, sidecar_path=sidecar_path)
    return sidecar


def _load_snapshot_sidecar_result(
    snapshot_path: str | Path,
    *,
    sidecar_path: str | Path | None = None,
) -> tuple[SnapshotSidecar, tuple[str, ...]]:
    snapshot_file = Path(snapshot_path)
    resolved_sidecar_path = Path(sidecar_path) if sidecar_path is not None else sidecar_path_for_snapshot(snapshot_file)

    try:
        payload = json.loads(resolved_sidecar_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SnapshotValidationError(f"missing sidecar: {resolved_sidecar_path}") from exc
    except json.JSONDecodeError as exc:
        raise SnapshotValidationError(f"invalid sidecar JSON: {resolved_sidecar_path}") from exc

    if not isinstance(payload, dict):
        raise SnapshotValidationError(f"sidecar must be a JSON object: {resolved_sidecar_path}")

    missing_fields = [field for field in ALLOWED_SIDECAR_FIELDS if field not in payload]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise SnapshotValidationError(f"sidecar missing required field(s): {missing}: {resolved_sidecar_path}")

    unexpected_fields = sorted(field for field in payload if field not in ALLOWED_SIDECAR_FIELDS)
    warnings: list[str] = []
    if unexpected_fields:
        extras = ", ".join(unexpected_fields)
        warnings.append(f"extra sidecar field(s) ignored: {extras}")

    profile = _require_str(payload, "profile", resolved_sidecar_path)
    source_url = _require_str(payload, "source_url", resolved_sidecar_path)
    expected_url = resolve_profile_url(profile)
    if source_url != expected_url:
        raise SnapshotValidationError(
            f"sidecar source_url does not match profile {profile!r}: {resolved_sidecar_path}"
        )

    fetched_at_utc = _require_str(payload, "fetched_at_utc", resolved_sidecar_path)
    _parse_utc_timestamp(fetched_at_utc, resolved_sidecar_path)

    status_code = payload["status_code"]
    if not isinstance(status_code, int) or not 200 <= status_code < 300:
        raise SnapshotValidationError(f"sidecar status_code must be a 2xx integer: {resolved_sidecar_path}")

    content_type = payload["content_type"]
    if content_type is not None and not isinstance(content_type, str):
        raise SnapshotValidationError(f"sidecar content_type must be a string or null: {resolved_sidecar_path}")
    if content_type is not None and not _is_xml_content_type(content_type):
        raise SnapshotValidationError(f"sidecar content_type must be XML: {resolved_sidecar_path}")

    etag = _require_optional_str(payload, "etag", resolved_sidecar_path)
    last_modified = _require_optional_str(payload, "last_modified", resolved_sidecar_path)
    sha256 = _require_str(payload, "sha256", resolved_sidecar_path)
    x_ms_schema_version = _require_optional_str(payload, "x_ms_schema_version", resolved_sidecar_path)

    actual_sha256 = hashlib.sha256(snapshot_file.read_bytes()).hexdigest()
    if sha256 != actual_sha256:
        raise SnapshotValidationError(
            f"sidecar sha256 does not match snapshot content: {resolved_sidecar_path}"
        )

    return (
        SnapshotSidecar(
            profile=profile,
            source_url=source_url,
            fetched_at_utc=fetched_at_utc,
            status_code=status_code,
            content_type=content_type,
            etag=etag,
            last_modified=last_modified,
            sha256=sha256,
            x_ms_schema_version=x_ms_schema_version,
        ),
        tuple(warnings),
    )


def _require_str(payload: dict[str, Any], field: str, sidecar_path: Path) -> str:
    value = payload[field]
    if not isinstance(value, str) or not value:
        raise SnapshotValidationError(f"sidecar field {field!r} must be a non-empty string: {sidecar_path}")
    return value


def _require_optional_str(payload: dict[str, Any], field: str, sidecar_path: Path) -> str | None:
    value = payload[field]
    if value is None:
        return None
    if not isinstance(value, str):
        raise SnapshotValidationError(f"sidecar field {field!r} must be a string or null: {sidecar_path}")
    return value


def _parse_utc_timestamp(value: str, sidecar_path: Path) -> None:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SnapshotValidationError(f"sidecar fetched_at_utc must be ISO-8601 UTC: {sidecar_path}") from exc


def _inspection_sort_key(inspection: SnapshotInspection) -> tuple[str, str, str, str]:
    profile = inspection.sidecar.profile if inspection.sidecar is not None else "\uffff"
    fetched_at_utc = inspection.sidecar.fetched_at_utc if inspection.sidecar is not None else "\uffff"
    xml_path = inspection.relative_path if inspection.relative_path.endswith(".xml") else inspection.snapshot_path.name
    return (profile, fetched_at_utc, xml_path, inspection.relative_path)


def _apply_duplicate_errors(inspections: list[SnapshotInspection]) -> list[SnapshotInspection]:
    grouped: dict[tuple[str, str, str], list[int]] = {}
    for index, inspection in enumerate(inspections):
        if inspection.sidecar is None:
            continue
        key = (
            inspection.sidecar.profile,
            inspection.sidecar.fetched_at_utc,
            inspection.sidecar.sha256,
        )
        grouped.setdefault(key, []).append(index)

    updated = list(inspections)
    for key, indexes in grouped.items():
        if len(indexes) < 2:
            continue
        message = (
            "duplicate snapshot metadata tuple "
            f"(profile={key[0]!r}, fetched_at_utc={key[1]!r}, sha256={key[2]!r})"
        )
        for index in indexes:
            updated[index] = replace(updated[index], errors=updated[index].errors + (message,))
    return updated
