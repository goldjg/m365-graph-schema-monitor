from __future__ import annotations

import json
import socket
from email.message import Message
from pathlib import Path
from urllib import error

import pytest

from graph_schema_monitor import cli
from graph_schema_monitor.fetcher import (
    FetchResult,
    HttpStatusError,
    InvalidProfileError,
    NetworkFailureError,
    OutputConflictError,
    RedirectNotAllowedError,
    UnexpectedContentTypeError,
    fetch_snapshot,
    resolve_profile_url,
)
from graph_schema_monitor.parser import parse_csdl_file


FIXTURE_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx" Version="4.0">
  <edmx:DataServices>
    <Schema Namespace="microsoft.graph" xmlns="http://docs.oasis-open.org/odata/ns/edm">
      <EntityType Name="conditionalAccessPolicy">
        <Property Name="id" Type="Edm.String" Nullable="false" />
        <Property Name="displayName" Type="Edm.String" />
      </EntityType>
    </Schema>
  </edmx:DataServices>
</edmx:Edmx>
"""
SIDECAR_FIELDS = [
    "profile",
    "source_url",
    "fetched_at_utc",
    "status_code",
    "content_type",
    "etag",
    "last_modified",
    "sha256",
    "x_ms_schema_version",
]


class FakeResponse:
    def __init__(self, body: bytes, *, status: int = 200, headers: dict[str, str] | None = None) -> None:
        self._body = body
        self._status = status
        self.headers = Message()
        for key, value in (headers or {}).items():
            self.headers[key] = value

    def read(self) -> bytes:
        return self._body

    def getcode(self) -> int:
        return self._status

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


class FakeOpener:
    def __init__(self, response: FakeResponse | Exception) -> None:
        self._response = response

    def open(self, url: str, timeout: int = 30) -> FakeResponse:
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


def test_resolve_profile_url_returns_allowlisted_urls() -> None:
    assert resolve_profile_url("v1.0") == "https://graph.microsoft.com/v1.0/$metadata"
    assert resolve_profile_url("beta") == "https://graph.microsoft.com/beta/$metadata"


def test_resolve_profile_url_rejects_unknown_profile() -> None:
    with pytest.raises(InvalidProfileError, match="Unknown profile"):
        resolve_profile_url("https://example.com/$metadata")


def test_fetch_snapshot_writes_files_and_returns_paths_only(tmp_path: Path) -> None:
    output_path = tmp_path / "snapshot.xml"
    opener = FakeOpener(
        FakeResponse(
            FIXTURE_XML,
            headers={
                "Content-Type": "application/xml; charset=utf-8",
                "ETag": '"etag-1"',
                "Last-Modified": "Fri, 30 May 2026 20:00:00 GMT",
                "x-ms-schemaVersion": "2026-05-30",
            },
        )
    )

    result = fetch_snapshot("v1.0", output_path, opener=opener)

    assert isinstance(result, FetchResult)
    assert not hasattr(result, "content")
    assert result.output_path == output_path
    assert result.sidecar_path == Path(f"{output_path}.json")
    assert output_path.read_bytes() == FIXTURE_XML

    sidecar = json.loads(result.sidecar_path.read_text(encoding="utf-8"))
    assert list(sidecar) == SIDECAR_FIELDS
    assert sidecar["profile"] == "v1.0"
    assert sidecar["source_url"] == "https://graph.microsoft.com/v1.0/$metadata"
    assert sidecar["status_code"] == 200
    assert sidecar["content_type"] == "application/xml; charset=utf-8"
    assert sidecar["etag"] == '"etag-1"'
    assert sidecar["last_modified"] == "Fri, 30 May 2026 20:00:00 GMT"
    assert sidecar["x_ms_schema_version"] == "2026-05-30"
    assert sidecar["sha256"] == result.sha256


def test_fetch_snapshot_rejects_existing_output_without_overwrite(tmp_path: Path) -> None:
    output_path = tmp_path / "snapshot.xml"
    output_path.write_text("existing", encoding="utf-8")

    with pytest.raises(OutputConflictError, match="Refusing to overwrite existing file"):
        fetch_snapshot("v1.0", output_path, opener=FakeOpener(FakeResponse(FIXTURE_XML)))


def test_fetch_snapshot_overwrites_existing_output_with_flag(tmp_path: Path) -> None:
    output_path = tmp_path / "snapshot.xml"
    output_path.write_text("existing", encoding="utf-8")
    Path(f"{output_path}.json").write_text("{}", encoding="utf-8")

    fetch_snapshot(
        "beta",
        output_path,
        overwrite=True,
        opener=FakeOpener(FakeResponse(FIXTURE_XML, headers={"Content-Type": "application/xml"})),
    )

    assert output_path.read_bytes() == FIXTURE_XML
    assert json.loads(Path(f"{output_path}.json").read_text(encoding="utf-8"))["profile"] == "beta"


@pytest.mark.parametrize("status_code", [404, 503])
def test_fetch_snapshot_rejects_http_errors(tmp_path: Path, status_code: int) -> None:
    http_error = error.HTTPError(
        url="https://graph.microsoft.com/v1.0/$metadata",
        code=status_code,
        msg="error",
        hdrs=None,
        fp=None,
    )

    with pytest.raises(HttpStatusError, match=f"HTTP status {status_code}"):
        fetch_snapshot("v1.0", tmp_path / "snapshot.xml", opener=FakeOpener(http_error))


def test_fetch_snapshot_rejects_timeout(tmp_path: Path) -> None:
    timeout_error = error.URLError(socket.timeout("timed out"))

    with pytest.raises(NetworkFailureError, match="Network timeout"):
        fetch_snapshot("v1.0", tmp_path / "snapshot.xml", opener=FakeOpener(timeout_error))


def test_fetch_snapshot_rejects_redirects(tmp_path: Path) -> None:
    with pytest.raises(RedirectNotAllowedError, match="Redirects are not allowed"):
        fetch_snapshot(
            "v1.0",
            tmp_path / "snapshot.xml",
            opener=FakeOpener(RedirectNotAllowedError("Redirects are not allowed to https://example.com.")),
        )


def test_fetch_snapshot_rejects_unexpected_content_type(tmp_path: Path) -> None:
    opener = FakeOpener(FakeResponse(FIXTURE_XML, headers={"Content-Type": "application/json"}))

    with pytest.raises(UnexpectedContentTypeError, match="Unexpected content type"):
        fetch_snapshot("v1.0", tmp_path / "snapshot.xml", opener=opener)


def test_fetch_snapshot_output_parses_with_existing_parser(tmp_path: Path) -> None:
    output_path = tmp_path / "snapshot.xml"
    fetch_snapshot(
        "v1.0",
        output_path,
        opener=FakeOpener(FakeResponse(FIXTURE_XML, headers={"Content-Type": "application/xml"})),
    )

    snapshot = parse_csdl_file(output_path)
    assert "microsoft.graph.conditionalAccessPolicy" in snapshot.types


def test_cli_fetch_writes_files_with_mocked_network(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    output_path = tmp_path / "snapshot.xml"
    monkeypatch.setattr(
        "graph_schema_monitor.fetcher.build_url_opener",
        lambda: FakeOpener(FakeResponse(FIXTURE_XML, headers={"Content-Type": "application/xml"})),
    )

    exit_code = cli.main(["fetch", "--profile", "v1.0", "--out", str(output_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert output_path.exists()
    assert Path(f"{output_path}.json").exists()
    assert "Fetched https://graph.microsoft.com/v1.0/$metadata" in captured.out


def test_cli_fetch_does_not_accept_url_argument(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(
            ["fetch", "--profile", "v1.0", "--url", "https://example.com/$metadata", "--out", "/tmp/out.xml"]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "unrecognized arguments: --url" in captured.err
