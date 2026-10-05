"""Collect guarded, view-only state evidence for an authorized authenticated audit.

This is deliberately supplementary to the production collector: it does not
change audit checks, scores, or report findings.  Each scenario starts from a
fresh authenticated page, blocks all unsafe HTTP methods, and captures only
the explicitly requested read-only UI states.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.audit.auth_session import configured_storage_state, looks_like_login_url, validate_authenticated_page
from src.audit.page_visit_helpers import wait_for_page_ready
from src.audit.workspace import AuditWorkspace, atomic_write_json
from src.main import launch_browser, new_isolated_context, workspace_config
from src.security.network_policy import sanitize_audit_ssl_keylogfile, validate_dependency_origin, validate_public_url


SCENARIOS = (
    ("desktop_base", False, None),
    ("desktop_filter_failed", False, "filter_failed"),
    ("desktop_search_no_results", False, "search_no_results"),
    ("desktop_sort_name", False, "sort_name"),
    ("desktop_pagination_page_2", False, "page_2"),
    ("desktop_view_documents", False, "view_documents"),
    ("mobile_base", True, None),
    ("mobile_filter_failed", True, "filter_failed"),
)


async def state_metrics(page) -> dict:
    return await page.evaluate(
        """() => ({
          title: document.title || '',
          textLength: (document.body?.innerText || '').trim().length,
          bodyLength: (document.body?.innerHTML || '').length,
          scrollWidth: document.documentElement?.scrollWidth || 0,
          viewportWidth: window.innerWidth || 0
        })"""
    )


async def run_action(page, action: str) -> None:
    if action == "filter_failed":
        await page.get_by_role("button", name="Failed (7)", exact=True).click(timeout=5_000)
    elif action == "search_no_results":
        search = page.get_by_placeholder("Search by TDR name...", exact=True)
        await search.fill("zzzzzzzzzz")
        await page.wait_for_timeout(500)
    elif action == "sort_name":
        await page.get_by_role("button", name="Nom", exact=True).click(timeout=5_000)
    elif action == "page_2":
        await page.get_by_role("button", name="2", exact=True).click(timeout=5_000)
    elif action == "view_documents":
        await page.get_by_role("button", name="Voir documents requis", exact=True).first.click(timeout=5_000)
    else:
        raise ValueError(f"Unsupported state action: {action}")
    await page.wait_for_timeout(750)


async def collect(args: argparse.Namespace) -> int:
    storage_state = configured_storage_state(args.storage_state)
    if storage_state is None:
        raise RuntimeError("A saved authenticated session is required.")

    workspace = AuditWorkspace.for_repository(args.job_id)
    config = workspace_config(workspace)
    primary = validate_public_url(args.url)
    dependencies = [validate_dependency_origin(value) for value in args.allowed_dependency_url]
    allowed = [primary, *dependencies]
    evidence_dir = workspace.screenshots / "state_evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    output_path = workspace.audit_dir / "authenticated_state_evidence.json"
    sanitize_audit_ssl_keylogfile()

    results = []
    async with async_playwright() as playwright:
        browser = await launch_browser(playwright, config, allowed)
        try:
            validation_context = await new_isolated_context(
                browser, config, allowed, storage_state=storage_state
            )
            try:
                await validate_authenticated_page(
                    validation_context, args.url, login_url=args.auth_login_url
                )
            finally:
                await validation_context.close()

            for scenario, mobile, action in SCENARIOS:
                context = await new_isolated_context(
                    browser, config, allowed, mobile=mobile, storage_state=storage_state
                )
                page = await context.new_page()
                blocked_mutations = []

                async def mutation_guard(route, request):
                    if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
                        blocked_mutations.append(request.method.upper())
                        await route.abort("blockedbyclient")
                        return
                    await route.continue_()

                await page.route("**/*", mutation_guard)
                item = {"scenario": scenario, "viewport": "mobile" if mobile else "desktop", "action": action or "base", "measurement": "measured"}
                try:
                    await page.goto(args.url, wait_until="domcontentloaded", timeout=20_000)
                    await wait_for_page_ready(page, config)
                    if looks_like_login_url(page.url, args.auth_login_url):
                        raise RuntimeError("Authenticated state redirected to login during state evidence collection.")
                    before = await state_metrics(page)
                    if action:
                        await run_action(page, action)
                    await wait_for_page_ready(page, config)
                    after = await state_metrics(page)
                    screenshot = evidence_dir / f"{scenario}.png"
                    await page.screenshot(path=str(screenshot), full_page=True)
                    item.update(
                        {
                            "status": "completed",
                            "finalUrl": page.url,
                            "domChanged": before["textLength"] != after["textLength"] or before["bodyLength"] != after["bodyLength"],
                            "horizontalOverflow": after["scrollWidth"] > after["viewportWidth"],
                            "screenshotPath": str(screenshot),
                            "networkWritesBlocked": blocked_mutations,
                        }
                    )
                except Exception as exc:
                    item.update({"status": "failed", "measurement": "collection_failed", "error": str(exc), "networkWritesBlocked": blocked_mutations})
                finally:
                    await context.close()
                results.append(item)
        finally:
            await browser.close()

    atomic_write_json(
        output_path,
        {
            "schemaVersion": 1,
            "auditId": workspace.job_id,
            "purpose": "guarded view-only authenticated UI state evidence",
            "scope": "single confirmed authenticated consultant route",
            "route": args.url,
            "finalRoute": "http://4.209.241.167/consultant/appels-offres",
            "allowedDependencyOrigins": [item.url for item in dependencies],
            "unsafeMethodsBlocked": ["POST", "PUT", "PATCH", "DELETE"],
            "results": results,
        },
    )
    print(f"State evidence manifest: {output_path}")
    print(f"Completed scenarios: {sum(item.get('status') == 'completed' for item in results)}/{len(results)}")
    return 0 if all(item.get("status") == "completed" for item in results) else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect guarded authenticated UI state evidence.")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--storage-state", required=True)
    parser.add_argument("--auth-login-url", required=True)
    parser.add_argument("--allowed-dependency-url", action="append", default=[])
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(collect(parse_args())))
