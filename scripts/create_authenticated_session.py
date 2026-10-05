"""Create a local Playwright storage state through a manually operated browser.

This utility is deliberately independent from the audit collector. It does
not install the collector's request routing or alter form controls, so an
operator can compare normal Chrome with Playwright Chromium safely.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from playwright.async_api import Browser, BrowserContext, async_playwright

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.audit.auth_session import (
    AUTH_RUNTIME_DIR,
    AuthenticationSessionError,
    default_storage_state_path,
    validate_authenticated_page,
)
from src.security.network_policy import validate_public_url


SAFE_MESSAGE_LIMIT = 500


def authenticated_default(login_url: str) -> str:
    parsed = urlsplit(login_url)
    return urlunsplit((parsed.scheme, parsed.netloc, "/", "", ""))


def safe_url(value: str) -> str:
    """Keep origin and path only; never store query or fragment values."""
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", "", ""))


def safe_message(value: object) -> str:
    """Make diagnostic text useful without retaining likely secrets."""
    message = str(value or "")
    message = re.sub(r"https?://[^\s'\"]+", lambda match: safe_url(match.group(0)), message)
    message = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[redacted-email]", message)
    message = re.sub(r"(?i)(authorization|cookie|password|token|secret|csrf|session|code|key)\s*[:=]\s*[^\s,;]+", r"\1=[redacted]", message)
    return message[:SAFE_MESSAGE_LIMIT]


def storage_destination(raw_path: str, login_url: str) -> Path:
    destination = Path(raw_path) if raw_path else default_storage_state_path(login_url)
    if not destination.is_absolute():
        destination = ROOT_DIR / destination
    destination = destination.resolve()
    try:
        destination.relative_to(AUTH_RUNTIME_DIR.resolve())
    except ValueError as exc:
        raise AuthenticationSessionError("Authenticated storage state must be saved under runtime/auth/.") from exc
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a local authenticated Playwright storage state without recording credentials.")
    parser.add_argument("--login-url", required=True)
    parser.add_argument("--authenticated-url", default="", help="Protected page used to validate a manually established session.")
    parser.add_argument("--storage-state", default="", help="Output path under runtime/auth/; defaults from the login host.")
    parser.add_argument(
        "--browser-channel",
        choices=("chromium", "chrome", "msedge"),
        default="chrome",
        help="Headed browser for manual login. 'chrome' uses installed Google Chrome when available.",
    )
    parser.add_argument(
        "--diagnostics-dir",
        default="",
        help="Optional ignored directory under runtime/auth/ for non-sensitive login diagnostics.",
    )
    return parser.parse_args()


def diagnostic_destination(raw_path: str, destination: Path) -> Path:
    diagnostics = Path(raw_path) if raw_path else destination.parent / "login-diagnostics"
    if not diagnostics.is_absolute():
        diagnostics = ROOT_DIR / diagnostics
    diagnostics = diagnostics.resolve()
    try:
        diagnostics.relative_to(AUTH_RUNTIME_DIR.resolve())
    except ValueError as exc:
        raise AuthenticationSessionError("Authentication diagnostics must be saved under runtime/auth/.") from exc
    return diagnostics


class LoginDiagnostics:
    """Capture only request metadata that cannot include submitted credentials."""

    def __init__(self, login_url: str, channel: str) -> None:
        self.login_url = safe_url(login_url)
        parsed = urlsplit(login_url)
        self.login_origin = f"{parsed.scheme}://{parsed.netloc}"
        self.channel = channel
        self.requests: list[dict[str, Any]] = []
        self.responses: list[dict[str, Any]] = []
        self.failed_requests: list[dict[str, Any]] = []
        self.console_errors: list[dict[str, str]] = []

    def attach(self, page) -> None:
        page.on("request", self._on_request)
        page.on("response", self._on_response)
        page.on("requestfailed", self._on_request_failed)
        page.on("console", self._on_console)

    def _is_login_request(self, url: str) -> bool:
        return safe_url(url) == self.login_url

    def _is_same_origin(self, url: str) -> bool:
        parsed = urlsplit(url)
        return f"{parsed.scheme}://{parsed.netloc}" == self.login_origin

    def _on_request(self, request) -> None:
        if self._is_login_request(request.url) or (self._is_same_origin(request.url) and request.method != "GET"):
            self.requests.append({"url": safe_url(request.url), "method": request.method})

    def _on_response(self, response) -> None:
        request = response.request
        if self._is_login_request(response.url) or (self._is_same_origin(response.url) and request.method != "GET"):
            self.responses.append(
                {
                    "url": safe_url(response.url),
                    "status": response.status,
                    "contentType": safe_message(response.headers.get("content-type", "")),
                    "redirectLocation": safe_url(response.headers.get("location", "")) if response.headers.get("location") else "",
                }
            )

    def _on_request_failed(self, request) -> None:
        self.failed_requests.append(
            {"url": safe_url(request.url), "method": request.method, "failure": safe_message(request.failure)}
        )

    def _on_console(self, message) -> None:
        if message.type == "error":
            self.console_errors.append({"type": "error", "message": safe_message(message.text)})

    def write(self, directory: Path, *, outcome: str, final_url: str) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        output = directory / "login-diagnostics.json"
        payload = {
            "capturedAt": datetime.now(timezone.utc).isoformat(),
            "browserChannel": self.channel,
            "outcome": outcome,
            "finalUrl": safe_url(final_url),
            "loginRequests": self.requests,
            "loginResponses": self.responses,
            "redirectChain": [item for item in self.responses if 300 <= int(item["status"]) < 400],
            "failedRequests": self.failed_requests,
            "consoleErrors": self.console_errors,
        }
        output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return output


async def validate_saved_state(browser: Browser, storage_state: Path, target_url: str, login_url: str) -> None:
    """Validate the exported state from a brand-new browser context."""
    fresh_context: BrowserContext = await browser.new_context(storage_state=str(storage_state), service_workers="allow")
    try:
        await validate_authenticated_page(fresh_context, target_url, login_url=login_url)
        verification_page = await fresh_context.new_page()
        try:
            await verification_page.goto(target_url, wait_until="domcontentloaded", timeout=20_000)
            if await verification_page.locator("body").count() != 1:
                raise AuthenticationSessionError("Authenticated application UI was not present in the fresh validation context.")
        finally:
            await verification_page.close()
    finally:
        await fresh_context.close()


async def async_main() -> None:
    args = parse_args()
    login = validate_public_url(args.login_url)
    target = validate_public_url(args.authenticated_url or authenticated_default(login.url))
    if login.hostname != target.hostname:
        raise AuthenticationSessionError("Authenticated validation URL must use the login host.")
    destination = storage_destination(args.storage_state, login.url)
    diagnostics_dir = diagnostic_destination(args.diagnostics_dir, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    channel = None if args.browser_channel == "chromium" else args.browser_channel
    diagnostics = LoginDiagnostics(login.url, args.browser_channel)
    outcome = "not_completed"
    final_url = login.url

    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch(headless=False, channel=channel)
        except Exception as exc:
            if channel:
                raise AuthenticationSessionError(
                    f"The requested {args.browser_channel} channel could not be launched. Use --browser-channel chromium or install that browser."
                ) from exc
            raise AuthenticationSessionError("The bundled Chromium browser could not be launched.") from exc

        context = await browser.new_context(service_workers="allow")
        page = await context.new_page()
        diagnostics.attach(page)
        try:
            await page.goto(login.url, wait_until="domcontentloaded", timeout=20_000)
            await asyncio.to_thread(
                input,
                "Manually complete one login attempt in the headed browser, then press Enter here. "
                "This utility never reads or submits credentials. ",
            )
            final_url = page.url
            try:
                await validate_authenticated_page(context, target.url, login_url=login.url)
                await context.storage_state(path=str(temporary))
                await validate_saved_state(browser, temporary, target.url, login.url)
                os.replace(temporary, destination)
                try:
                    os.chmod(destination, 0o600)
                except OSError:
                    pass
                outcome = "authenticated_session_validated"
                print(f"Authenticated session saved: {destination.relative_to(AUTH_RUNTIME_DIR.parent)}")
            except AuthenticationSessionError:
                outcome = "authentication_not_validated"
                raise
        finally:
            temporary.unlink(missing_ok=True)
            diagnostic_file = diagnostics.write(diagnostics_dir, outcome=outcome, final_url=final_url)
            await context.close()
            await browser.close()
            print(f"Non-sensitive login diagnostics: {diagnostic_file.relative_to(AUTH_RUNTIME_DIR.parent)}")


if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except AuthenticationSessionError as exc:
        raise SystemExit(f"Authentication session was not created: {exc}") from exc
    except Exception:
        raise SystemExit("Authentication session was not created. Inspect the ignored non-sensitive diagnostics and retry only when safe.")
