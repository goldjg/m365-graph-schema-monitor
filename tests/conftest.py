from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from urllib import request

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def block_live_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    def _blocked_open(self: request.OpenerDirector, fullurl: object, data: object = None, timeout: object = None) -> object:
        raise AssertionError(f"Live network access is not allowed in tests: {fullurl}")

    monkeypatch.setattr(request.OpenerDirector, "open", _blocked_open)
    yield
