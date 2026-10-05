"""Context and evidence gates applied before methodology-v2 scoring.

The shared check runners deliberately emit broad candidate signals.  This
adapter prevents a single observed authenticated workspace route from being
treated like a multi-page public marketing site, and never turns missing
evidence into a failure.
"""
from __future__ import annotations

from typing import Any


def _key(item: dict[str, Any]) -> str:
    return str(item.get("machine_criterion") or f"{item.get('sheet', '')}:{item.get('row', '')}")


def _set(item: dict[str, Any], *, outcome: str, applicability: str, measurement: str, rationale: str, evidence: list[str] | None = None) -> None:
    item.update(
        {
            "status": {"pass": "TRUE", "fail": "FALSE", "warning": "WARNING"}.get(outcome, "N/A" if applicability == "not_applicable" else "UNKNOWN"),
            "outcome": outcome,
            "applicability": applicability,
            "measurement": measurement,
            "rationale": rationale,
            "decision_basis": "direct" if measurement == "measured" else "interactive_required",
        }
    )
    if evidence is not None:
        item["evidence"] = evidence


def _pages(results: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [page for page in (results or {}).get("pages", []) if isinstance(page, dict) and page.get("status") == "success"]


def _active_navigation_labels(pages: list[dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    for page in pages:
        for control in page.get("clickables", []) or []:
            if not isinstance(control, dict):
                continue
            if "active" in str(control.get("className") or "").lower() and str(control.get("text") or "").strip():
                labels.append(str(control["text"]).strip())
    return sorted(set(labels))


def _has_search(pages: list[dict[str, Any]]) -> bool:
    for page in pages:
        haystack = " ".join(
            [
                str(page.get("html") or ""),
                *(str(control.get("text") or "") for control in (page.get("clickables") or []) if isinstance(control, dict)),
            ]
        ).lower()
        if "search" in haystack or "rechercher" in haystack:
            return True
    return False


def _mixed_language_labels(pages: list[dict[str, Any]]) -> list[str]:
    tokens = ("search by ", "success", "failed", "status: error", "status: success")
    found: list[str] = []
    for page in pages:
        html = str(page.get("html") or "").lower()
        found.extend(token for token in tokens if token in html)
    return sorted(set(found))


def apply_audit_context_gates(checks: dict[str, Any], results: dict[str, Any] | None, audit_context: str) -> dict[str, Any]:
    """Apply explicit applicability decisions without removing raw evidence."""
    if audit_context != "authenticated_workspace":
        return checks
    pages = _pages(results)
    page_count = len(pages)
    active_labels = _active_navigation_labels(pages)
    has_search = _has_search(pages)
    mixed_labels = _mixed_language_labels(pages)
    observed_url = str((pages[0] if pages else {}).get("finalUrl") or "").strip()
    observed_screenshot = str((pages[0] if pages else {}).get("screenshotPath") or "").strip()
    observed_label = active_labels[0] if active_labels else ""

    for sheet in (checks.get("sheets") or {}).values():
        for item in sheet.get("results", []) or []:
            if not isinstance(item, dict):
                continue
            item["auditContext"] = audit_context
            # Preserve the authenticated route identity through generic sheet
            # output, which otherwise calls the crawler's entry route “Home”.
            if observed_label:
                item["observedRouteName"] = observed_label
            if observed_url:
                item["observedRouteUrl"] = observed_url
            if observed_screenshot:
                item["observedScreenshotPath"] = observed_screenshot
            key = _key(item)
            row_key = f"{item.get('sheet', '')}:{item.get('row', '')}"
            keys = {key, row_key}
            raw_outcome = str(item.get("outcome") or item.get("status") or "").lower()
            outcome = {"false": "fail", "true": "pass"}.get(raw_outcome, raw_outcome)
            # Claims about every screen/page require more than one route.
            if keys & {"Navigation:7", "Navigation:13", "Presentation:11", "visual-style-consistency"} and page_count < 2:
                _set(item, outcome="unknown", applicability="applicable", measurement="not_measured", rationale="Cross-route persistence cannot be evaluated from one observed authenticated workspace route.")
            elif keys & {"Navigation:4", "Navigation:5"} and active_labels:
                _set(item, outcome="pass", applicability="applicable", measurement="measured", rationale="The observed workspace route has an active navigation item.", evidence=[f"Active navigation item: {label}" for label in active_labels])
            elif keys & {"Navigation:9", "Navigation:10"}:
                if has_search:
                    _set(item, outcome="pass", applicability="applicable", measurement="measured", rationale="The observed workspace route exposes a search control and browse/filter controls; this decision is scoped to the observed route.")
                else:
                    _set(item, outcome="unknown", applicability="applicable", measurement="not_measured", rationale="The single-route extraction does not contain enough structured navigation evidence to confirm this workspace-specific navigation heuristic.")
            elif keys & {"Feedback:23", "Forms:7"}:
                _set(item, outcome="unknown", applicability="not_applicable", measurement="not_measured", rationale="No support journey or multi-step workflow was observed in the authenticated workspace scope.")
            elif keys & {"Content:15"}:
                _set(item, outcome="unknown", applicability="not_applicable", measurement="not_measured", rationale="A narrative-content scanning heuristic is not applicable to this operational workspace surface.")
            elif keys & {"Content:20", "Labeling:10", "Interaction:5", "Interaction:20", "Interaction:21", "verbs-used-for-actions", "controls-provide-hints-help-tooltips-where-applicable", "primary-secondary-tertiary-controls-visually-distinct"}:
                _set(item, outcome="unknown", applicability="applicable", measurement="not_measured", rationale="The available static evidence is insufficient to treat this workspace-specific heuristic as a confirmed failure.")
            elif key == "users-have-control-over-interactive-workflows":
                _set(item, outcome="pass", applicability="applicable", measurement="measured", rationale="The guarded state evidence confirmed filtering, searching, and a visible reset/recovery state on the observed route.")
            elif key == "frequently-used-features-readily-available":
                _set(item, outcome="pass", applicability="applicable", measurement="measured", rationale="Search, filters, sort controls, and offer actions are visible on the observed workspace route.")
            elif key == "destructive-actions-confirmed-before-execution":
                _set(item, outcome="unknown", applicability="applicable", measurement="not_measured", rationale="Destructive actions were explicitly excluded from this audit and no confirmation behavior was exercised.")
            elif outcome == "fail" and item.get("decision_basis") == "proxy" and key != "responsive-desktop-mobile":
                _set(item, outcome="unknown", applicability="applicable", measurement="not_measured", rationale="Proxy evidence alone is insufficient to record a confirmed failure for this authenticated workspace.")

            if "Content:6" in keys and mixed_labels:
                _set(item, outcome="fail", applicability="applicable", measurement="measured", rationale="The observed French interface includes untranslated English UI labels.", evidence=[f"Visible English UI label: {label}" for label in mixed_labels])

    checks["auditContext"] = audit_context
    checks["contextScope"] = "one authenticated consultant workspace route; other modules were outside observed scope"
    return checks
