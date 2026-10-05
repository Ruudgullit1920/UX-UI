"""Bounded, mutation-blocked follow-up for one authenticated workspace route."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audit.auth_session import configured_storage_state, looks_like_login_url, validate_authenticated_page
from src.audit.axe_runner import run_axe
from src.audit.page_visit_helpers import wait_for_page_ready
from src.audit.workspace import AuditWorkspace, atomic_write_json
from src.main import launch_browser, new_isolated_context, workspace_config
from src.security.network_policy import sanitize_audit_ssl_keylogfile, validate_dependency_origin, validate_public_url


async def safe_metrics(page):
    return await page.evaluate(r"""() => ({
      url: location.href, title: document.title || '',
      text: (document.body?.innerText || '').replace(/\s+/g, ' ').trim(),
      scrollWidth: document.documentElement.scrollWidth, viewportWidth: innerWidth,
      buttons: Array.from(document.querySelectorAll('button')).filter(el => el.offsetParent).map(el => ({text: (el.innerText || el.getAttribute('aria-label') || '').trim(), ariaPressed: el.getAttribute('aria-pressed'), ariaCurrent: el.getAttribute('aria-current'), className: el.className || '', dataState: el.getAttribute('data-state') || ''})).slice(0, 100)
    })""")


async def assert_authenticated(page, login_url: str) -> None:
    if looks_like_login_url(page.url, login_url):
        raise RuntimeError("STOP_SESSION_EXPIRED: redirected to login; no further follow-up actions were attempted.")


async def keyboard_probe(page, screenshot_dir: Path) -> dict:
    """Traverse a bounded tab sequence using a DOM-unique fingerprint."""
    inventory = await page.evaluate(r"""() => {
      const clean = value => String(value || '').replace(/\s+/g, ' ').trim();
      const pathFor = el => {
        const parts = [];
        for (let node = el; node && node.nodeType === 1 && parts.length < 8; node = node.parentElement) {
          const siblings = Array.from(node.parentElement?.children || []).filter(x => x.tagName === node.tagName);
          parts.unshift(`${node.tagName.toLowerCase()}:nth-of-type(${siblings.indexOf(node) + 1})`);
        }
        return parts.join(' > ');
      };
      const visible = el => { const r = el.getBoundingClientRect(), s = getComputedStyle(el); return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden'; };
      return Array.from(document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, summary, [role=button], [role=link], [role=tab], [role=menuitem], [tabindex]:not([tabindex="-1"])'))
        .filter(el => visible(el) && !el.disabled && el.getAttribute('aria-hidden') !== 'true')
        .slice(0, 160).map((el, index) => ({index, tag: el.tagName.toLowerCase(), role: clean(el.getAttribute('role')), label: clean(el.getAttribute('aria-label') || el.innerText || el.textContent || el.getAttribute('title') || el.name || el.id || el.href), selector: pathFor(el), tabIndex: el.tabIndex}));
    }""")
    await page.evaluate("document.activeElement?.blur?.()")
    reached, seen, weak = [], set(), []
    reason = "tab_budget_exhausted"
    for sequence in range(1, 81):
        await page.keyboard.press("Tab")
        item = await page.evaluate(r"""() => {
          const el = document.activeElement;
          if (!el || el === document.body || el === document.documentElement) return null;
          const clean = value => String(value || '').replace(/\s+/g, ' ').trim();
          const pathFor = el => { const parts=[]; for(let node=el; node && node.nodeType===1 && parts.length<8; node=node.parentElement){ const siblings=Array.from(node.parentElement?.children || []).filter(x=>x.tagName===node.tagName); parts.unshift(`${node.tagName.toLowerCase()}:nth-of-type(${siblings.indexOf(node)+1})`); } return parts.join(' > '); };
          const s = getComputedStyle(el), r = el.getBoundingClientRect();
          const outline = parseFloat(s.outlineWidth || '0') || 0, shadow = String(s.boxShadow || '');
          const focusVisible = el.matches(':focus-visible');
          return {tag:el.tagName.toLowerCase(), role:clean(el.getAttribute('role')), label:clean(el.getAttribute('aria-label') || el.innerText || el.textContent || el.getAttribute('title') || el.name || el.id || el.href), selector:pathFor(el), tabIndex:el.tabIndex, focusVisible, outlineWidth:outline, boxShadow:shadow.slice(0,120), focusIndicatorCss: outline >= 2 || (shadow && shadow !== 'none'), rect:{left:Math.round(r.left),right:Math.round(r.right),top:Math.round(r.top),bottom:Math.round(r.bottom)}};
        }""")
        if item is None:
            continue
        if item["selector"] in seen:
            reason = "focus_cycle_detected"
            break
        seen.add(item["selector"])
        item["sequence"] = sequence
        # CSS is an objective proxy; screenshots retain visual evidence for review.
        item["visuallyPerceivable"] = "css_indicator_present" if item["focusVisible"] and item["focusIndicatorCss"] else "needs_visual_review"
        reached.append(item)
        if item["visuallyPerceivable"] != "css_indicator_present":
            weak.append(item)
    shot = screenshot_dir / "keyboard_final_focus.png"
    await page.screenshot(path=str(shot), full_page=False)
    return {"status": "measured", "interactiveCount": len(inventory), "reachedCount": len(reached), "coverage": round(len(reached) / len(inventory) * 100, 1) if inventory else 100.0, "tabBudget": 80, "terminationReason": reason, "reached": reached, "weakFocusSamples": weak[:12], "focusScreenshot": str(shot), "limitations": ["Traversal does not activate controls.", "CSS focus signals and the retained screenshot require human visual confirmation when no indicator is detected."]}


async def action_state(page, label: str, screenshot_dir: Path, filename: str) -> dict:
    before = await safe_metrics(page)
    locator = page.get_by_role("button", name=label, exact=True).first
    if await locator.count() != 1 or not await locator.is_visible():
        return {"status": "not_measured", "reason": f"Safe control '{label}' was not uniquely visible."}
    await locator.click(timeout=5_000)
    await page.wait_for_timeout(700)
    await assert_authenticated(page, "")
    after = await safe_metrics(page)
    shot = screenshot_dir / filename
    await page.screenshot(path=str(shot), full_page=True)
    ui_state_changed = before["buttons"] != after["buttons"]
    return {"status": "measured", "entryControl": label, "beforeText": before["text"][:1000], "afterText": after["text"][:1000], "domChanged": before["text"] != after["text"], "uiStateChanged": ui_state_changed, "urlChanged": before["url"] != after["url"], "finalUrl": after["url"], "screenshotPath": str(shot)}


async def collect(args: argparse.Namespace) -> None:
    state = configured_storage_state(args.storage_state)
    if state is None:
        raise RuntimeError("A saved authenticated session is required.")
    workspace = AuditWorkspace.for_repository(args.job_id)
    config = workspace_config(workspace)
    primary = validate_public_url(args.url)
    dependencies = [validate_dependency_origin(value) for value in args.allowed_dependency_url]
    allowed = [primary, *dependencies]
    output_dir = workspace.screenshots / "targeted_followup"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = workspace.audit_dir / "authenticated_targeted_followup.json"
    sanitize_audit_ssl_keylogfile()
    result = {"schemaVersion": 1, "auditId": args.job_id, "scope": "bounded authenticated follow-up; no write/destructive/logout actions", "route": args.url, "allowedDependencyOrigins": [item.url for item in dependencies], "keyboard": None, "sorting": None, "pagination": None, "detail": None, "mobile": None, "axe": {}, "status": "completed"}
    async with async_playwright() as playwright:
        browser = await launch_browser(playwright, config, allowed)
        try:
            context = await new_isolated_context(browser, config, allowed, storage_state=state)
            page = await context.new_page()
            blocked = []
            async def mutation_guard(route, request):
                if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
                    blocked.append(request.method.upper()); await route.abort("blockedbyclient"); return
                await route.continue_()
            await page.route("**/*", mutation_guard)
            await validate_authenticated_page(context, args.url, login_url=args.auth_login_url)
            await page.goto(args.url, wait_until="domcontentloaded", timeout=20_000); await wait_for_page_ready(page, config); await assert_authenticated(page, args.auth_login_url)
            result["keyboard"] = await keyboard_probe(page, output_dir)
            await page.goto(args.url, wait_until="domcontentloaded", timeout=20_000); await wait_for_page_ready(page, config); await assert_authenticated(page, args.auth_login_url)
            result["sorting"] = await action_state(page, "Nom", output_dir, "sort_name.png")
            await page.goto(args.url, wait_until="domcontentloaded", timeout=20_000); await wait_for_page_ready(page, config); await assert_authenticated(page, args.auth_login_url)
            result["pagination"] = await action_state(page, "2", output_dir, "pagination_page_2.png")
            await page.goto(args.url, wait_until="domcontentloaded", timeout=20_000); await wait_for_page_ready(page, config); await assert_authenticated(page, args.auth_login_url)
            result["detail"] = await action_state(page, "Voir documents requis", output_dir, "detail_documents.png")
            # This button is explicitly view-only. Measure the opened detail state
            # before resetting the route; do not activate either modal action.
            if result["detail"].get("status") == "measured":
                result["axe"]["detail"] = await run_axe(page, page_id="authenticated_targeted_detail")
            await page.goto(args.url, wait_until="domcontentloaded", timeout=20_000); await wait_for_page_ready(page, config); await assert_authenticated(page, args.auth_login_url)
            result["axe"]["base"] = await run_axe(page, page_id="authenticated_targeted_base")
            mobile_context = await new_isolated_context(browser, config, allowed, mobile=True, storage_state=state)
            mobile = await mobile_context.new_page(); await mobile.route("**/*", mutation_guard)
            await mobile.goto(args.url, wait_until="domcontentloaded", timeout=20_000); await wait_for_page_ready(mobile, config); await assert_authenticated(mobile, args.auth_login_url)
            result["mobile"] = await mobile.evaluate(r"""() => { const w=innerWidth; const visible=el=>{const r=el.getBoundingClientRect(),s=getComputedStyle(el);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden'}; return {viewportWidth:w,scrollWidth:document.documentElement.scrollWidth,documentHorizontalOverflowPx:Math.max(0,document.documentElement.scrollWidth-w),outsideViewport:Array.from(document.querySelectorAll('a,button,input,select,textarea,[role=button]')).filter(visible).map(el=>{const r=el.getBoundingClientRect();return {tag:el.tagName.toLowerCase(),label:(el.getAttribute('aria-label')||el.innerText||el.textContent||'').trim().slice(0,120),left:Math.round(r.left),right:Math.round(r.right),outsideLeft:Math.max(0,Math.round(-r.left)),outsideRight:Math.max(0,Math.round(r.right-w))}}).filter(x=>x.outsideLeft||x.outsideRight)} }""")
            mobile_shot = output_dir / "mobile_final.png"; await mobile.screenshot(path=str(mobile_shot), full_page=True); result["mobile"]["screenshotPath"] = str(mobile_shot)
            result["axe"]["mobile"] = await run_axe(mobile, page_id="authenticated_targeted_mobile")
            await mobile_context.close(); result["blockedMutationMethods"] = blocked
            await context.close()
        except Exception as exc:
            result["status"] = "stopped" if "STOP_SESSION_EXPIRED" in str(exc) else "failed"; result["error"] = str(exc)
        finally:
            await browser.close()
    atomic_write_json(output, result)
    print(f"Targeted evidence: {output}")
    print(f"Status: {result['status']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True); parser.add_argument("--url", required=True)
    parser.add_argument("--storage-state", required=True); parser.add_argument("--auth-login-url", required=True)
    parser.add_argument("--allowed-dependency-url", action="append", default=[])
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(collect(parse_args()))
