"""Run a bounded, non-sensitive authenticated browser preflight."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.audit.auth_session import AuthenticationSessionError, resolve_storage_state, validate_authenticated_page
from src.audit.axe_runner import run_axe
from src.security.network_policy import chromium_host_resolver_rules, install_playwright_network_guard, validate_public_url


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate an authenticated session and collect one local diagnostic screenshot.")
    parser.add_argument("url")
    parser.add_argument("--storage-state", required=True)
    parser.add_argument("--login-url", default="")
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()
    target = validate_public_url(args.url)
    state = resolve_storage_state(args.storage_state)
    assert state is not None
    diagnostics = state.parent / "preflight"
    diagnostics.mkdir(parents=True, exist_ok=True)
    screenshot = diagnostics / "authenticated-page.png"
    summary = diagnostics / "summary.json"
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, args=[f"--host-resolver-rules={chromium_host_resolver_rules([target])}"])
        context = await browser.new_context(storage_state=str(state), viewport={"width": 1440, "height": 900}, service_workers="block")
        await install_playwright_network_guard(context, [target])
        page = await context.new_page()
        try:
            await validate_authenticated_page(context, target.url, login_url=args.login_url)
            response = await page.goto(target.url, wait_until="domcontentloaded", timeout=20_000)
            await page.screenshot(path=str(screenshot), full_page=True)
            axe = await run_axe(page, page_id="authenticated_preflight")
            navigation_count = await page.locator("nav a, [role='navigation'] a, aside a").count()
            summary.write_text(json.dumps({"status": "passed", "httpStatus": int(response.status) if response else None, "navigationElements": navigation_count, "axeStatus": axe.get("status"), "axeMeasurement": axe.get("measurement"), "screenshot": str(screenshot.relative_to(state.parent))}, indent=2) + "\n", encoding="utf-8")
            print(f"Authenticated preflight passed. Diagnostics: {diagnostics.relative_to(Path.cwd())}")
        finally:
            await context.close()
            await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except AuthenticationSessionError as exc:
        raise SystemExit(f"Authenticated preflight failed: {exc}") from exc
