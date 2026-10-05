"""Bounded production-component evidence collection for public auth pages.

This collector never enters credentials, never creates an account, and blocks all
state-changing HTTP methods before a request can leave the browser.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import sys
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audit.axe_runner import run_axe
from src.audit.page_visit_helpers import wait_for_page_ready
from src.audit.workspace import AuditWorkspace, atomic_write_json
from src.main import launch_browser, new_isolated_context, workspace_config
from src.security.network_policy import sanitize_audit_ssl_keylogfile, validate_public_url


FORM_SNAPSHOT = r"""() => {
  const clean = value => String(value || '').replace(/\s+/g, ' ').trim();
  const visible = el => {
    const rect = el.getBoundingClientRect(), style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  };
  const selector = el => {
    if (el.id) return `#${CSS.escape(el.id)}`;
    const parts = [];
    for (let node = el; node && node.nodeType === 1 && parts.length < 7; node = node.parentElement) {
      const siblings = Array.from(node.parentElement?.children || []).filter(item => item.tagName === node.tagName);
      parts.unshift(`${node.tagName.toLowerCase()}:nth-of-type(${siblings.indexOf(node) + 1})`);
    }
    return parts.join(' > ');
  };
  const textFor = el => {
    const byFor = el.id ? Array.from(document.querySelectorAll(`label[for="${CSS.escape(el.id)}"]`)).map(label => clean(label.innerText || label.textContent)) : [];
    const wrapping = el.closest('label');
    return [...byFor, wrapping ? clean(wrapping.innerText || wrapping.textContent) : ''].filter(Boolean);
  };
  const describedBy = el => clean(el.getAttribute('aria-describedby')).split(' ').filter(Boolean).map(id => ({ id, text: clean(document.getElementById(id)?.innerText || document.getElementById(id)?.textContent) }));
  const control = el => {
    const rect = el.getBoundingClientRect();
    return {
      tag: el.tagName.toLowerCase(), selector: selector(el), id: el.id || '', name: el.getAttribute('name') || '',
      type: el.getAttribute('type') || '', autocomplete: el.getAttribute('autocomplete') || '', required: el.required === true,
      ariaLabel: el.getAttribute('aria-label') || '', ariaLabelledBy: el.getAttribute('aria-labelledby') || '',
      ariaDescribedBy: el.getAttribute('aria-describedby') || '', labels: textFor(el), describedBy: describedBy(el),
      disabled: el.disabled === true, tabIndex: el.tabIndex, width: Math.round(rect.width), height: Math.round(rect.height),
      visible: visible(el), validationMessage: el.validationMessage || ''
    };
  };
  const inputs = Array.from(document.querySelectorAll('input, textarea, select')).filter(visible).map(control);
  const buttons = Array.from(document.querySelectorAll('button')).filter(visible).map(el => ({ ...control(el), text: clean(el.innerText || el.textContent), ariaPressed: el.getAttribute('aria-pressed'), role: el.getAttribute('role') || '' }));
  const links = Array.from(document.querySelectorAll('a[href]')).filter(visible).map(el => ({ text: clean(el.innerText || el.textContent), href: el.href, ariaLabel: el.getAttribute('aria-label') || '', tabIndex: el.tabIndex }));
  return { url: location.href, title: document.title || '', inputs, buttons, links, documentLanguage: document.documentElement.lang || '' };
}"""


VISUAL_METRICS = r"""() => {
  const clean = value => String(value || '').replace(/\s+/g, ' ').trim();
  const visible = el => { const r=el.getBoundingClientRect(), s=getComputedStyle(el); return r.width>0 && r.height>0 && s.display !== 'none' && s.visibility !== 'hidden'; };
  const element = el => { const r=el.getBoundingClientRect(), s=getComputedStyle(el); return { tag:el.tagName.toLowerCase(), text:clean(el.innerText || el.textContent || el.getAttribute('aria-label')).slice(0,140), role:el.getAttribute('role') || '', type:el.getAttribute('type') || '', left:Math.round(r.left), right:Math.round(r.right), top:Math.round(r.top), bottom:Math.round(r.bottom), width:Math.round(r.width), height:Math.round(r.height), color:s.color, backgroundColor:s.backgroundColor, fontSize:s.fontSize, fontWeight:s.fontWeight }; };
  const candidates = Array.from(document.querySelectorAll('a,button,input,textarea,select,label,p,small,span')).filter(visible);
  return { viewport:{width:innerWidth,height:innerHeight}, scrollWidth:document.documentElement.scrollWidth, horizontalOverflowPx:Math.max(0,document.documentElement.scrollWidth-innerWidth), outsideViewport:candidates.map(element).filter(item => item.right > innerWidth || item.left < 0), visualControls:candidates.map(element).filter(item => item.tag === 'button' || item.tag === 'input' || item.tag === 'a') };
}"""


async def discover_signup(page, login_url: str) -> str:
    links = await page.evaluate(
        r"""() => {
          const selector = el => {
            if (el.id) return `#${CSS.escape(el.id)}`;
            const parts = [];
            for (let node = el; node && node.nodeType === 1 && parts.length < 7; node = node.parentElement) {
              const siblings = Array.from(node.parentElement?.children || []).filter(item => item.tagName === node.tagName);
              parts.unshift(`${node.tagName.toLowerCase()}:nth-of-type(${siblings.indexOf(node) + 1})`);
            }
            return parts.join(' > ');
          };
          return Array.from(document.querySelectorAll('a[href], button, [role="link"], [role="button"]')).filter(el => {
          const r=el.getBoundingClientRect(), s=getComputedStyle(el);
          return r.width>0 && r.height>0 && s.display !== 'none' && s.visibility !== 'hidden';
        }).map(el => ({tag:el.tagName.toLowerCase(), text:(el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim(), href:el.href || '', selector:selector(el)}));
        }"""
    )
    for link in links:
        label = str(link.get("text") or "").casefold().replace("’", "'")
        if "s'inscrire" in label or "inscrire" in label:
            href = str(link.get("href") or "")
            if href:
                return urljoin(login_url, href)
            locator = page.locator(str(link.get("selector") or ""))
            if await locator.count() == 1:
                await locator.click(timeout=5_000)
                await page.wait_for_timeout(500)
                if page.url != login_url:
                    return page.url
            text_locator = page.get_by_text(str(link.get("text") or ""), exact=True)
            if await text_locator.count() == 1:
                await text_locator.click(timeout=5_000)
                await page.wait_for_timeout(500)
                if page.url != login_url:
                    return page.url
    labels = ", ".join(str(item.get("text") or "")[:80] for item in links)
    raise RuntimeError(f"Registration route was not discoverable from a visible S'inscrire link. Visible controls: {labels}")


async def blank_validation_probe(page) -> dict:
    """Trigger only native/client validation; mutation requests remain blocked."""
    before = await page.evaluate(r"""() => ({ invalid: Array.from(document.querySelectorAll('input,textarea,select')).filter(el => el.matches(':invalid')).map(el => ({name:el.name || el.id || el.type, message:el.validationMessage || ''})), text:(document.body?.innerText || '').replace(/\s+/g,' ').trim().slice(0,2400) })""")
    submit = page.locator("form button[type='submit'], form input[type='submit']")
    count = await submit.count()
    if count != 1:
        return {"status": "not_measured", "reason": f"Expected one submit control; found {count}.", "before": before}
    if await submit.is_disabled():
        return {
            "status": "not_measured",
            "reason": "Submit control is disabled in the empty state; no enabled safe validation path was available without entering data.",
            "before": before,
        }
    await submit.click(timeout=5_000)
    after = await page.evaluate(r"""() => ({ invalid: Array.from(document.querySelectorAll('input,textarea,select')).filter(el => el.matches(':invalid')).map(el => ({name:el.name || el.id || el.type, message:el.validationMessage || '', ariaInvalid:el.getAttribute('aria-invalid'), describedBy:el.getAttribute('aria-describedby')})), text:(document.body?.innerText || '').replace(/\s+/g,' ').trim().slice(0,2400) })""")
    return {"status": "measured", "before": before, "after": after, "note": "Blank submission only; network mutation guard blocked all state-changing requests."}


async def keyboard_inventory(page) -> dict:
    return await page.evaluate(r"""() => {
      const clean = value => String(value || '').replace(/\s+/g, ' ').trim();
      const visible = el => { const r=el.getBoundingClientRect(), s=getComputedStyle(el); return r.width>0 && r.height>0 && s.display !== 'none' && s.visibility !== 'hidden'; };
      return Array.from(document.querySelectorAll('a[href],button,input:not([type=hidden]),select,textarea,[role=button],[tabindex]:not([tabindex="-1"])')).filter(el => visible(el) && !el.disabled).map((el,index) => ({ index, tag:el.tagName.toLowerCase(), type:el.getAttribute('type') || '', label:clean(el.getAttribute('aria-label') || el.innerText || el.textContent || el.name || el.id), tabIndex:el.tabIndex, href:el.href || '' }));
    }""")


async def collect_page(page, *, name: str, url: str, screenshots: Path, width: int) -> dict:
    await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
    await wait_for_page_ready(page, {"pageReadiness": {"networkIdleTimeoutMs": 3_000, "assetTimeoutMs": 3_000, "settleDelayMs": 250}})
    stem = "login" if name == "Connexion" else "registration"
    screenshot = screenshots / f"{stem}-{width}.png"
    await page.screenshot(path=str(screenshot), full_page=True)
    semantics = await page.evaluate(FORM_SNAPSHOT)
    visual = await page.evaluate(VISUAL_METRICS)
    validation = await blank_validation_probe(page)
    return {
        "name": name,
        "route": page.url,
        "viewportWidth": width,
        "screenshotPath": str(screenshot),
        "form": semantics,
        "visual": visual,
        "keyboardOrder": await keyboard_inventory(page),
        "blankValidation": validation,
        "axe": await run_axe(page, page_id=f"public_auth_{stem}_{width}"),
    }


async def collect(args: argparse.Namespace) -> None:
    workspace = AuditWorkspace.for_repository(args.job_id)
    workspace.prepare(mode="website")
    config = workspace_config(workspace)
    login = validate_public_url(args.login_url)
    screenshots = workspace.screenshots / "public_auth"
    screenshots.mkdir(parents=True, exist_ok=True)
    result = {
        "schemaVersion": 1,
        "auditId": workspace.job_id,
        "scope": "Two public auth pages only. No credentials entered; account creation and all state-changing requests blocked.",
        "loginRoute": login.url,
        "registrationRoute": "",
        "blockedMutationMethods": [],
        "pages": [],
        "status": "completed",
    }
    sanitize_audit_ssl_keylogfile()
    async with async_playwright() as playwright:
        browser = await launch_browser(playwright, config, [login])
        try:
            discovery_context = await new_isolated_context(browser, config, [login])
            discovery_page = await discovery_context.new_page()
            await discovery_page.goto(login.url, wait_until="domcontentloaded", timeout=20_000)
            await wait_for_page_ready(discovery_page, config)
            registration_url = await discover_signup(discovery_page, login.url)
            registration = validate_public_url(registration_url)
            if registration.hostname != login.hostname:
                raise RuntimeError("Visible registration link points outside the approved audit host.")
            result["registrationRoute"] = registration.url
            await discovery_context.close()

            async def mutation_guard(route, request):
                if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
                    result["blockedMutationMethods"].append(request.method.upper())
                    await route.abort("blockedbyclient")
                    return
                await route.continue_()

            for width in (1440, 390, 430):
                page_config = config
                if width != 1440:
                    # Use a literal CSS viewport for responsive evidence.  Mobile
                    # emulation alone can mask a missing viewport declaration by
                    # expanding layout viewport width before the page is measured.
                    page_config = copy.deepcopy(config)
                    page_config["browser"]["viewport"] = {"width": width, "height": 844}
                context = await new_isolated_context(browser, page_config, [login], mobile=False)
                page = await context.new_page()
                await page.route("**/*", mutation_guard)
                result["pages"].append(await collect_page(page, name="Connexion", url=login.url, screenshots=screenshots, width=width))
                result["pages"].append(await collect_page(page, name="Créer un compte consultant", url=registration.url, screenshots=screenshots, width=width))
                await context.close()
        except Exception as error:
            result["status"] = "failed"
            result["error"] = str(error)
        finally:
            await browser.close()
    result["blockedMutationMethods"] = sorted(set(result["blockedMutationMethods"]))
    output = workspace.audit_dir / "public_auth_targeted_audit.json"
    atomic_write_json(output, result)
    print(f"Public auth targeted evidence: {output}")
    print(f"Status: {result['status']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect bounded public auth-page audit evidence.")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--login-url", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(collect(parse_args()))
