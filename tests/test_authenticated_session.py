from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path

import pytest

from src.audit import auth_session


ROOT_DIR = Path(__file__).resolve().parents[1]


def load_session_launcher():
    spec = importlib.util.spec_from_file_location(
        "authenticated_session_launcher_under_test",
        ROOT_DIR / "scripts" / "create_authenticated_session.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_storage_state_is_limited_to_ignored_auth_runtime(tmp_path, monkeypatch):
    runtime_dir = tmp_path / "runtime" / "auth"
    state = runtime_dir / "4.209.241.167" / "session.json"
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps({"cookies": [{}], "origins": []}), encoding="utf-8")
    monkeypatch.setattr(auth_session, "AUTH_RUNTIME_DIR", runtime_dir)

    assert auth_session.resolve_storage_state(state) == state.resolve()

    outside = tmp_path / "session.json"
    outside.write_text(json.dumps({"cookies": [{}], "origins": []}), encoding="utf-8")
    with pytest.raises(auth_session.AuthenticationSessionError, match="runtime/auth"):
        auth_session.resolve_storage_state(outside)


@pytest.mark.parametrize("payload", [{}, {"cookies": "not-a-list"}, {"cookies": [], "origins": []}])
def test_storage_state_must_be_nonempty_playwright_json(tmp_path, monkeypatch, payload):
    runtime_dir = tmp_path / "runtime" / "auth"
    state = runtime_dir / "host" / "session.json"
    state.parent.mkdir(parents=True)
    state.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(auth_session, "AUTH_RUNTIME_DIR", runtime_dir)

    with pytest.raises(auth_session.AuthenticationSessionError):
        auth_session.resolve_storage_state(state)


def test_login_redirect_detection_uses_explicit_and_standard_paths():
    assert auth_session.looks_like_login_url(
        "http://4.209.241.167/auth/login", "http://4.209.241.167/auth/login"
    )
    assert auth_session.looks_like_login_url("http://example.test/sign-in")
    assert not auth_session.looks_like_login_url("http://example.test/reports/42")


def test_login_diagnostics_strip_query_values_and_likely_sensitive_text(tmp_path):
    launcher = load_session_launcher()
    diagnostics = launcher.LoginDiagnostics("http://4.209.241.167/auth/login", "chrome")
    output = diagnostics.write(
        tmp_path,
        outcome="authentication_not_validated",
        final_url="http://4.209.241.167/auth/login?opaque=value",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["finalUrl"] == "http://4.209.241.167/auth/login"
    assert launcher.safe_message("password=private-value csrf=opaque email=user@example.test") == "password=[redacted] csrf=[redacted] email=[redacted-email]"
    assert launcher.safe_url("http://4.209.241.167/auth/login?opaque=value#fragment") == "http://4.209.241.167/auth/login"
