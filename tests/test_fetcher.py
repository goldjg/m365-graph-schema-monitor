from __future__ import annotations

import json
import os
import socket
from email.message import Message
from pathlib import Path
from urllib import error, request as urllib_request

import pytest

from graph_schema_monitor import cli
from graph_schema_monitor.fetcher import (
    AuthFetchResult,
    FetchResult,
    HttpStatusError,
    InvalidProfileError,
    NetworkFailureError,
    OutputConflictError,
    RedirectNotAllowedError,
    TokenError,
    UnexpectedContentTypeError,
    fetch_authenticated_snapshot,
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

    def open(self, url_or_request: object, data: object = None, timeout: int = 30) -> FakeResponse:
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


class FakeCapturingOpener:
    """Like FakeOpener but also records the last Request object passed to open()."""

    def __init__(self, response: FakeResponse | Exception) -> None:
        self._response = response
        self.last_request: urllib_request.Request | None = None

    def open(self, req: object, data: object = None, timeout: int = 30) -> FakeResponse:
        if isinstance(req, urllib_request.Request):
            self.last_request = req
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


def test_cli_fetch_writes_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
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


# ─── CA-2: authenticated fetch uses fixed allowlisted URLs only ──────────────

def test_auth_fetch_rejects_unknown_profile_before_env_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_accessed: list[str] = []
    original_get = os.environ.get

    # Set env var BEFORE patching get, so setenv itself doesn't appear in tracking
    monkeypatch.setenv("MY_TOKEN", "tok")

    def tracking_get(key: str, *args: object) -> object:
        env_accessed.append(key)
        return original_get(key, *args)

    monkeypatch.setattr(os.environ, "get", tracking_get)

    with pytest.raises(InvalidProfileError, match="Unknown profile"):
        fetch_authenticated_snapshot(
            "unknown",
            tmp_path / "out.xml",
            token_env="MY_TOKEN",
        )

    assert "MY_TOKEN" not in env_accessed


def test_auth_fetch_does_not_accept_url_argument(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(
            ["fetch-auth", "--profile", "v1.0", "--url", "https://example.com/$metadata",
             "--out", str(tmp_path / "out.xml"), "--token-env", "MY_TOKEN"]
        )
    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "unrecognized arguments: --url" in captured.err


def test_auth_fetch_rejects_redirects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MY_TOKEN", "tok")
    opener = FakeCapturingOpener(RedirectNotAllowedError("Redirects are not allowed."))

    with pytest.raises(RedirectNotAllowedError, match="Redirects are not allowed"):
        fetch_authenticated_snapshot(
            "v1.0",
            tmp_path / "out.xml",
            token_env="MY_TOKEN",
            opener=opener,
        )


# ─── CA-3: token handling non-persistent / non-observable ────────────────────

def test_auth_fetch_sends_authorization_header(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_token = "test-access-token-value-12345"
    monkeypatch.setenv("MY_TOKEN", test_token)
    opener = FakeCapturingOpener(
        FakeResponse(
            FIXTURE_XML,
            headers={"Content-Type": "application/xml"},
        )
    )

    fetch_authenticated_snapshot(
        "v1.0",
        tmp_path / "out.xml",
        token_env="MY_TOKEN",
        opener=opener,
    )

    assert opener.last_request is not None
    auth_header = opener.last_request.get_header("Authorization")
    assert auth_header is not None
    assert auth_header.startswith("Bearer ")
    # Verify the actual token value was sent (not a placeholder)
    assert test_token in auth_header


def test_auth_fetch_result_contains_no_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_token = "secret-token-must-not-appear-in-result"
    monkeypatch.setenv("MY_TOKEN", test_token)
    opener = FakeCapturingOpener(
        FakeResponse(FIXTURE_XML, headers={"Content-Type": "application/xml"})
    )

    result = fetch_authenticated_snapshot(
        "v1.0",
        tmp_path / "out.xml",
        token_env="MY_TOKEN",
        opener=opener,
    )

    result_repr = repr(result)
    assert test_token not in result_repr
    for field in result.__dataclass_fields__:
        value = getattr(result, field)
        if isinstance(value, str):
            assert test_token not in value


def test_auth_fetch_sidecar_contains_no_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_token = "secret-token-must-not-appear-in-sidecar"
    monkeypatch.setenv("MY_TOKEN", test_token)
    output_path = tmp_path / "out.xml"
    opener = FakeCapturingOpener(
        FakeResponse(FIXTURE_XML, headers={"Content-Type": "application/xml"})
    )

    fetch_authenticated_snapshot(
        "v1.0",
        output_path,
        token_env="MY_TOKEN",
        opener=opener,
    )

    sidecar_text = Path(f"{output_path}.json").read_text(encoding="utf-8")
    assert test_token not in sidecar_text


def test_auth_token_error_message_contains_no_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_token = "secret-token-must-not-appear-in-error"
    monkeypatch.setenv("MY_TOKEN", test_token)

    # Simulate HTTP 401 — error message must not contain the token
    opener = FakeCapturingOpener(
        error.HTTPError(
            url="https://graph.microsoft.com/v1.0/$metadata",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )
    )

    with pytest.raises(HttpStatusError) as exc_info:
        fetch_authenticated_snapshot(
            "v1.0",
            tmp_path / "out.xml",
            token_env="MY_TOKEN",
            opener=opener,
        )

    assert test_token not in str(exc_info.value)


# ─── CA-4: authenticated sidecar provenance is compatible ────────────────────

def test_auth_fetch_sidecar_loadable_by_load_snapshot_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from graph_schema_monitor.snapshots import load_snapshot_bundle

    monkeypatch.setenv("MY_TOKEN", "tok")
    output_path = tmp_path / "auth.xml"
    opener = FakeCapturingOpener(
        FakeResponse(FIXTURE_XML, headers={"Content-Type": "application/xml", "x-ms-schemaVersion": "2026-05-30"})
    )

    fetch_authenticated_snapshot(
        "v1.0",
        output_path,
        token_env="MY_TOKEN",
        tenant_label="lab",
        opener=opener,
    )

    bundle = load_snapshot_bundle(output_path)
    assert bundle.sidecar is not None
    assert bundle.sidecar.profile == "v1.0"
    assert bundle.sidecar.source_url == "https://graph.microsoft.com/v1.0/$metadata"
    assert bundle.sidecar.status_code == 200
    assert bundle.sidecar.x_ms_schema_version == "2026-05-30"


def test_auth_fetch_sidecar_warns_on_extra_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from graph_schema_monitor.snapshots import inspect_snapshot_file

    monkeypatch.setenv("MY_TOKEN", "tok")
    output_path = tmp_path / "auth.xml"
    opener = FakeCapturingOpener(
        FakeResponse(FIXTURE_XML, headers={"Content-Type": "application/xml"})
    )

    fetch_authenticated_snapshot(
        "v1.0",
        output_path,
        token_env="MY_TOKEN",
        opener=opener,
    )

    inspection = inspect_snapshot_file(output_path)
    assert not inspection.errors
    assert any("extra sidecar field(s) ignored" in w for w in inspection.warnings)


def test_auth_fetch_sidecar_extra_fields_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MY_TOKEN", "tok")
    output_path = tmp_path / "auth.xml"
    opener = FakeCapturingOpener(
        FakeResponse(FIXTURE_XML, headers={"Content-Type": "application/xml"})
    )

    fetch_authenticated_snapshot(
        "v1.0",
        output_path,
        token_env="MY_TOKEN",
        tenant_label="my-lab",
        opener=opener,
    )

    sidecar = json.loads(Path(f"{output_path}.json").read_text(encoding="utf-8"))
    assert sidecar["source_kind"] == "authenticated_graph_metadata"
    assert sidecar["auth_mode"] == "env_token"
    assert sidecar["tenant_label"] == "my-lab"


def test_auth_fetch_sidecar_tenant_label_null_when_omitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MY_TOKEN", "tok")
    output_path = tmp_path / "auth.xml"
    opener = FakeCapturingOpener(
        FakeResponse(FIXTURE_XML, headers={"Content-Type": "application/xml"})
    )

    fetch_authenticated_snapshot(
        "v1.0",
        output_path,
        token_env="MY_TOKEN",
        opener=opener,
    )

    sidecar = json.loads(Path(f"{output_path}.json").read_text(encoding="utf-8"))
    assert sidecar["tenant_label"] is None


def test_public_sidecar_no_extra_field_warnings(tmp_path: Path) -> None:
    from graph_schema_monitor.snapshots import inspect_snapshot_file

    output_path = tmp_path / "pub.xml"
    opener = FakeOpener(
        FakeResponse(FIXTURE_XML, headers={"Content-Type": "application/xml"})
    )

    fetch_snapshot("v1.0", output_path, opener=opener)

    inspection = inspect_snapshot_file(output_path)
    assert not inspection.errors
    assert not any("extra sidecar field(s) ignored" in w for w in inspection.warnings)


# ─── CA-5: no new network surface ─────────────────────────────────────────────

def test_auth_fetch_no_live_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MY_TOKEN", "tok")
    opener = FakeCapturingOpener(
        FakeResponse(FIXTURE_XML, headers={"Content-Type": "application/xml"})
    )

    # Monkeypatch socket.socket to ensure no real network calls occur
    def _no_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("Real network socket created during test")

    monkeypatch.setattr(socket, "socket", _no_network)

    fetch_authenticated_snapshot(
        "v1.0",
        tmp_path / "out.xml",
        token_env="MY_TOKEN",
        opener=opener,
    )


# ─── Token failure tests ──────────────────────────────────────────────────────

def test_auth_fetch_missing_token_env_arg(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["fetch-auth", "--profile", "v1.0", "--out", str(tmp_path / "out.xml")])
    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "--token-env" in captured.err


def test_auth_fetch_env_var_not_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISSING_TOKEN_VAR", raising=False)

    with pytest.raises(TokenError, match="not set: MISSING_TOKEN_VAR"):
        fetch_authenticated_snapshot(
            "v1.0",
            tmp_path / "out.xml",
            token_env="MISSING_TOKEN_VAR",
        )


def test_auth_fetch_env_var_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMPTY_TOKEN_VAR", "")

    with pytest.raises(TokenError, match="empty: EMPTY_TOKEN_VAR"):
        fetch_authenticated_snapshot(
            "v1.0",
            tmp_path / "out.xml",
            token_env="EMPTY_TOKEN_VAR",
        )


def test_auth_fetch_env_var_whitespace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WS_TOKEN_VAR", "   ")

    with pytest.raises(TokenError, match="empty: WS_TOKEN_VAR"):
        fetch_authenticated_snapshot(
            "v1.0",
            tmp_path / "out.xml",
            token_env="WS_TOKEN_VAR",
        )


# ─── Profile / URL control tests ─────────────────────────────────────────────

def test_auth_fetch_rejects_http_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MY_TOKEN", "tok")
    http_error = error.HTTPError(
        url="https://graph.microsoft.com/v1.0/$metadata",
        code=403,
        msg="Forbidden",
        hdrs=None,
        fp=None,
    )

    with pytest.raises(HttpStatusError, match="HTTP 403"):
        fetch_authenticated_snapshot(
            "v1.0",
            tmp_path / "out.xml",
            token_env="MY_TOKEN",
            opener=FakeCapturingOpener(http_error),
        )


def test_auth_fetch_rejects_unexpected_content_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MY_TOKEN", "tok")
    opener = FakeCapturingOpener(
        FakeResponse(FIXTURE_XML, headers={"Content-Type": "application/json"})
    )

    with pytest.raises(UnexpectedContentTypeError, match="Unexpected content type"):
        fetch_authenticated_snapshot(
            "v1.0",
            tmp_path / "out.xml",
            token_env="MY_TOKEN",
            opener=opener,
        )


# ─── Overwrite / file behaviour tests ────────────────────────────────────────

def test_auth_fetch_existing_output_no_overwrite_fails_before_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MY_TOKEN", "tok")
    output_path = tmp_path / "out.xml"
    output_path.write_text("existing", encoding="utf-8")

    # Use a capturing opener so we can verify it was never called
    opener = FakeCapturingOpener(
        FakeResponse(FIXTURE_XML, headers={"Content-Type": "application/xml"})
    )

    with pytest.raises(OutputConflictError, match="Refusing to overwrite"):
        fetch_authenticated_snapshot(
            "v1.0",
            output_path,
            token_env="MY_TOKEN",
            opener=opener,
        )

    assert opener.last_request is None


def test_auth_fetch_existing_output_with_overwrite_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MY_TOKEN", "tok")
    output_path = tmp_path / "out.xml"
    output_path.write_text("existing", encoding="utf-8")
    Path(f"{output_path}.json").write_text("{}", encoding="utf-8")
    opener = FakeCapturingOpener(
        FakeResponse(FIXTURE_XML, headers={"Content-Type": "application/xml"})
    )

    result = fetch_authenticated_snapshot(
        "v1.0",
        output_path,
        token_env="MY_TOKEN",
        overwrite=True,
        opener=opener,
    )

    assert result.output_path.read_bytes() == FIXTURE_XML


# ─── Success path tests ───────────────────────────────────────────────────────

def test_auth_fetch_writes_files_and_returns_auth_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MY_TOKEN", "tok-value-12345")
    output_path = tmp_path / "auth.xml"
    opener = FakeCapturingOpener(
        FakeResponse(
            FIXTURE_XML,
            headers={
                "Content-Type": "application/xml; charset=utf-8",
                "ETag": '"etag-auth"',
                "Last-Modified": "Fri, 30 May 2026 20:00:00 GMT",
                "x-ms-schemaVersion": "2026-05-30",
            },
        )
    )

    result = fetch_authenticated_snapshot(
        "v1.0",
        output_path,
        token_env="MY_TOKEN",
        tenant_label="lab",
        opener=opener,
    )

    assert isinstance(result, AuthFetchResult)
    assert result.output_path == output_path
    assert result.sidecar_path == Path(f"{output_path}.json")
    assert output_path.read_bytes() == FIXTURE_XML
    assert result.profile == "v1.0"
    assert result.source_url == "https://graph.microsoft.com/v1.0/$metadata"
    assert result.source_kind == "authenticated_graph_metadata"
    assert result.auth_mode == "env_token"
    assert result.tenant_label == "lab"
    assert result.x_ms_schema_version == "2026-05-30"
    assert result.etag == '"etag-auth"'

    sidecar = json.loads(result.sidecar_path.read_text(encoding="utf-8"))
    assert sidecar["profile"] == "v1.0"
    assert sidecar["source_url"] == "https://graph.microsoft.com/v1.0/$metadata"
    assert sidecar["status_code"] == 200
    assert sidecar["x_ms_schema_version"] == "2026-05-30"
    assert sidecar["source_kind"] == "authenticated_graph_metadata"
    assert sidecar["auth_mode"] == "env_token"
    assert sidecar["tenant_label"] == "lab"
    # Token must not appear anywhere in the sidecar (use a distinctive value not a substring of field names)
    assert "tok-value-12345" not in json.dumps(sidecar)


def test_auth_fetch_sha256_matches_content(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import hashlib

    monkeypatch.setenv("MY_TOKEN", "tok")
    output_path = tmp_path / "auth.xml"
    opener = FakeCapturingOpener(
        FakeResponse(FIXTURE_XML, headers={"Content-Type": "application/xml"})
    )

    result = fetch_authenticated_snapshot(
        "v1.0",
        output_path,
        token_env="MY_TOKEN",
        opener=opener,
    )

    expected = hashlib.sha256(FIXTURE_XML).hexdigest()
    assert result.sha256 == expected
    sidecar = json.loads(result.sidecar_path.read_text(encoding="utf-8"))
    assert sidecar["sha256"] == expected


# ─── CLI integration tests ────────────────────────────────────────────────────

def test_cli_fetch_auth_success_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("MY_TOKEN", "tok")
    output_path = tmp_path / "auth.xml"
    monkeypatch.setattr(
        "graph_schema_monitor.fetcher.build_url_opener",
        lambda: FakeCapturingOpener(
            FakeResponse(FIXTURE_XML, headers={"Content-Type": "application/xml"})
        ),
    )

    exit_code = cli.main(
        [
            "fetch-auth",
            "--profile", "v1.0",
            "--out", str(output_path),
            "--token-env", "MY_TOKEN",
            "--tenant-label", "lab",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert output_path.exists()
    assert Path(f"{output_path}.json").exists()
    assert "Fetched authenticated https://graph.microsoft.com/v1.0/$metadata" in captured.out
    assert "Sidecar:" in captured.out
    # Token value must not appear in output
    assert "tok" not in captured.out
    assert "tok" not in captured.err


def test_cli_fetch_auth_env_var_not_set_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("ABSENT_TOKEN", raising=False)
    output_path = tmp_path / "auth.xml"

    exit_code = cli.main(
        [
            "fetch-auth",
            "--profile", "v1.0",
            "--out", str(output_path),
            "--token-env", "ABSENT_TOKEN",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "ABSENT_TOKEN" in captured.err
    assert not output_path.exists()
