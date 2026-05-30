from __future__ import annotations

import hashlib
import json
import os
import socket
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request


PROFILE_URLS = {
    "v1.0": "https://graph.microsoft.com/v1.0/$metadata",
    "beta": "https://graph.microsoft.com/beta/$metadata",
}
DEFAULT_TIMEOUT_SECONDS = 30
ALLOWED_HOST = "graph.microsoft.com"
ALLOWED_SIDECAR_FIELDS = (
    "profile",
    "source_url",
    "fetched_at_utc",
    "status_code",
    "content_type",
    "etag",
    "last_modified",
    "sha256",
    "x_ms_schema_version",
)


@dataclass(frozen=True)
class FetchResult:
    profile: str
    source_url: str
    fetched_at_utc: str
    status_code: int
    content_type: str | None
    etag: str | None
    last_modified: str | None
    sha256: str
    x_ms_schema_version: str | None
    output_path: Path
    sidecar_path: Path


class FetchError(Exception):
    exit_code = 1


class InvalidProfileError(FetchError):
    exit_code = 2


class OutputConflictError(FetchError):
    exit_code = 2


class RedirectNotAllowedError(FetchError):
    pass


class HttpStatusError(FetchError):
    pass


class NetworkFailureError(FetchError):
    pass


class UnexpectedContentTypeError(FetchError):
    pass


class WriteFailureError(FetchError):
    pass


class _NoRedirectHandler(request.HTTPRedirectHandler):
    def _reject(self, headers: Any) -> None:
        location = headers.get("Location")
        target = f" to {location}" if location else ""
        raise RedirectNotAllowedError(f"Redirects are not allowed{target}.")

    def http_error_301(self, req: Any, fp: Any, code: int, msg: str, headers: Any) -> Any:
        self._reject(headers)

    def http_error_302(self, req: Any, fp: Any, code: int, msg: str, headers: Any) -> Any:
        self._reject(headers)

    def http_error_303(self, req: Any, fp: Any, code: int, msg: str, headers: Any) -> Any:
        self._reject(headers)

    def http_error_307(self, req: Any, fp: Any, code: int, msg: str, headers: Any) -> Any:
        self._reject(headers)

    def http_error_308(self, req: Any, fp: Any, code: int, msg: str, headers: Any) -> Any:
        self._reject(headers)


def build_url_opener() -> request.OpenerDirector:
    return request.build_opener(_NoRedirectHandler())


def resolve_profile_url(profile: str) -> str:
    try:
        url = PROFILE_URLS[profile]
    except KeyError as exc:
        allowed = ", ".join(sorted(PROFILE_URLS))
        raise InvalidProfileError(f"Unknown profile '{profile}'. Allowed values: {allowed}.") from exc

    _validate_allowlisted_url(url)
    return url


def fetch_snapshot(
    profile: str,
    out_path: str | Path,
    *,
    overwrite: bool = False,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    opener: request.OpenerDirector | None = None,
) -> FetchResult:
    source_url = resolve_profile_url(profile)
    output_path = Path(out_path)
    sidecar_path = Path(f"{output_path}.json")
    _validate_output_paths(output_path, sidecar_path, overwrite=overwrite)

    active_opener = opener or build_url_opener()
    try:
        with active_opener.open(source_url, timeout=timeout) as response:
            status_code = response.getcode()
            if status_code is None or not 200 <= status_code < 300:
                raise HttpStatusError(f"Fetch failed with HTTP status {status_code}.")

            content_type = response.headers.get("Content-Type")
            if not _is_xml_content_type(content_type):
                raise UnexpectedContentTypeError(
                    f"Unexpected content type: {content_type or 'missing Content-Type header'}."
                )

            content = response.read()
            fetched_at_utc = _utc_now_iso8601()
            sha256 = hashlib.sha256(content).hexdigest()
            etag = response.headers.get("ETag")
            last_modified = response.headers.get("Last-Modified")
            x_ms_schema_version = response.headers.get("x-ms-schemaVersion")
    except error.HTTPError as exc:
        raise HttpStatusError(f"Fetch failed with HTTP status {exc.code}.") from exc
    except RedirectNotAllowedError:
        raise
    except error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, TimeoutError | socket.timeout):
            raise NetworkFailureError(f"Network timeout after {timeout} seconds.") from exc
        raise NetworkFailureError(f"Network error: {reason}.") from exc
    except socket.timeout as exc:
        raise NetworkFailureError(f"Network timeout after {timeout} seconds.") from exc

    sidecar_payload = {
        "profile": profile,
        "source_url": source_url,
        "fetched_at_utc": fetched_at_utc,
        "status_code": status_code,
        "content_type": content_type,
        "etag": etag,
        "last_modified": last_modified,
        "sha256": sha256,
        "x_ms_schema_version": x_ms_schema_version,
    }
    _write_file(output_path, content)
    _write_file(sidecar_path, _render_sidecar_json(sidecar_payload).encode("utf-8"))

    return FetchResult(
        profile=profile,
        source_url=source_url,
        fetched_at_utc=fetched_at_utc,
        status_code=status_code,
        content_type=content_type,
        etag=etag,
        last_modified=last_modified,
        sha256=sha256,
        x_ms_schema_version=x_ms_schema_version,
        output_path=output_path,
        sidecar_path=sidecar_path,
    )


def _validate_allowlisted_url(url: str) -> None:
    parsed = parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
        raise FetchError(f"URL is outside the allowed HTTPS Graph boundary: {url}.")


def _validate_output_paths(output_path: Path, sidecar_path: Path, *, overwrite: bool) -> None:
    parent = output_path.parent
    if not parent.exists() or not parent.is_dir():
        raise WriteFailureError(f"Output directory does not exist: {parent}.")

    conflicts = [path for path in (output_path, sidecar_path) if path.exists()]
    if conflicts and not overwrite:
        raise OutputConflictError(f"Refusing to overwrite existing file: {conflicts[0]}. Use --overwrite.")


def _is_xml_content_type(content_type: str | None) -> bool:
    if content_type is None:
        return False
    media_type = content_type.split(";", 1)[0].strip().lower()
    return media_type in {"application/xml", "text/xml"} or media_type.endswith("+xml")


def _utc_now_iso8601() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _render_sidecar_json(payload: dict[str, Any]) -> str:
    ordered_payload = {field: payload[field] for field in ALLOWED_SIDECAR_FIELDS}
    return json.dumps(ordered_payload, indent=2)


def _write_file(path: Path, content: bytes) -> None:
    temp_path: str | None = None
    try:
        fd, temp_path = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
        os.replace(temp_path, path)
    except OSError as exc:
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        raise WriteFailureError(f"Failed to write file: {path}.") from exc
