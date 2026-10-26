"""Unit tests for bootstrap_admin redirect helpers (no network)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap_admin.py"


def _load_bootstrap():
    spec = importlib.util.spec_from_file_location("bootstrap_admin", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_redirect_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SITE_URL", raising=False)
    monkeypatch.delenv("NEXT_PUBLIC_SITE_URL", raising=False)
    mod = _load_bootstrap()
    assert (
        mod._redirect_to()
        == "https://job-hunt-agent-eta.vercel.app/auth/callback?next=/auth/set-password"
    )


def test_redirect_to_respects_site_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SITE_URL", "https://example.test/")
    mod = _load_bootstrap()
    assert mod._redirect_to() == "https://example.test/auth/callback?next=/auth/set-password"
