"""Optional, local-only Playwright storage-state support for authorized audits."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit


ROOT_DIR = Path(__file__).resolve().parents[2]
AUTH_RUNTIME_DIR = ROOT_DIR / "runtime" / "auth"
_LOGIN_SEGMENT = re.compile(r"(?:^|/)(?:auth/)?(?:login|signin|sign-in)(?:/|$)", re.IGNORECASE)


class AuthenticationSessionError(RuntimeError):
    """Raised when an optional authenticated audit session cannot be used safely."""


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def default_storage_state_path(login_url: str) -> Path:
    hostname = urlsplit(login_url).hostname or "session"
    safe_host = re.sub(r"[^a-zA-Z0-9.-]+", "_", hostname).strip("._") or "session"
    return AUTH_RUNTIME_DIR / safe_host / "session.json"


def resolve_storage_state(raw_path: str | Path | None) -> Path | None:
    """Validate an optional local state file without ever returning its contents."""
    if raw_path is None or not str(raw_path).strip():
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = ROOT_DIR / candidate
    resolved = candidate.resolve()
    if not _inside(resolved, AUTH_RUNTIME_DIR):
        raise AuthenticationSessionError("Authenticated storage state must be stored under runtime/auth/.")
    if candidate.is_symlink() or not resolved.is_file():
        raise AuthenticationSessionError("Authenticated storage state is missing or is not a regular file.")
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuthenticationSessionError("Authenticated storage state is unreadable or malformed.") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("cookies", []), list) or not isinstance(payload.get("origins", []), list):
        raise AuthenticationSessionError("Authenticated storage state has an invalid Playwright format.")
    if not payload.get("cookies") and not payload.get("origins"):
        raise AuthenticationSessionError("Authenticated storage state is empty; establish a new session.")
    return resolved


def configured_storage_state(raw_path: str | Path | None = None) -> Path | None:
    return resolve_storage_state(raw_path if raw_path is not None else os.getenv("UX_AUDIT_STORAGE_STATE", ""))


def looks_like_login_url(url: str, login_url: str = "") -> bool:
    parsed = urlsplit(url)
    if login_url:
        expected = urlsplit(login_url)
        if parsed.scheme == expected.scheme and parsed.netloc == expected.netloc and parsed.path.rstrip("/") == expected.path.rstrip("/"):
            return True
    return bool(_LOGIN_SEGMENT.search(parsed.path or ""))


async def validate_authenticated_page(context, url: str, *, login_url: str = "", timeout_ms: int = 15_000) -> None:
    """Prove a state reaches protected content before collection starts.

    The function deliberately reports no cookies, headers, tokens, page text, or URL query values.
    """
    page = await context.new_page()
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        if response is None:
            raise AuthenticationSessionError("Authenticated target did not return a document response.")
        status = int(response.status) if response is not None else 0
        if status in {401, 403}:
            raise AuthenticationSessionError("Authenticated target returned an HTTP authentication failure.")
        if status >= 400:
            raise AuthenticationSessionError(f"Authenticated target returned HTTP {status}.")
        if looks_like_login_url(page.url, login_url):
            raise AuthenticationSessionError("Authenticated session redirected to the login page. Establish a new session.")
    finally:
        await page.close()
