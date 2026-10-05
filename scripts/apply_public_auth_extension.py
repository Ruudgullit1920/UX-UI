"""Merge accepted bounded public-auth evidence into the stakeholder payload.

The collector data is already complete when this runs; this module never opens a
browser or contacts the audited site.  It preserves the historical workspace
evidence and augments it with the two explicitly approved public auth pages.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audit.workspace import atomic_write_json


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def page(data: dict, route: str, width: int) -> dict:
    for item in data.get("pages") or []:
        if item.get("route") == route and item.get("viewportWidth") == width:
            return item
    raise ValueError(f"Missing measured auth page: {route} at {width}px")


def finding(*, axis_id: str, axis_name: str, title: str, severity: str, page_name: str, page_url: str, evidence: str, why: str, recommendation: str, screenshot: Path, annotation: str, bundle: dict) -> dict:
    return {
        "axisId": axis_id,
        "axisName": axis_name,
        "title": title,
        "severity": severity,
        "confidence": 0.95,
        "pageName": page_name,
        "pageUrl": page_url,
        "evidence": evidence,
        "explanation": evidence,
        "whyItMatters": why,
        "recommendation": recommendation,
        "screenshotPath": str(screenshot),
        "evidenceAnnotation": annotation,
        "measurementClass": "standards_automated" if annotation == "password-control" else "rendered_evidence",
        "evidenceBundle": bundle,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-dir", required=True)
    parser.add_argument("--auth-evidence", required=True)
    args = parser.parse_args()
    job = Path(args.job_dir).resolve()
    payload_path = job / "audit" / "gtm_audit.json"
    payload = load(payload_path)
    auth = load(Path(args.auth_evidence).resolve())
    if auth.get("status") != "completed":
        raise ValueError("Public-auth evidence must be completed before it can be merged.")

    login = str(auth["loginRoute"])
    registration = str(auth["registrationRoute"])
    login_desktop, login_mobile = page(auth, login, 1440), page(auth, login, 390)
    registration_desktop, registration_mobile = page(auth, registration, 1440), page(auth, registration, 390)
    auth_dir = job / "screenshots" / "public_auth"
    auth_dir.mkdir(parents=True, exist_ok=True)
    for item, name in ((login_desktop, "login-1440.png"), (login_mobile, "login-390.png"), (registration_desktop, "registration-1440.png"), (registration_mobile, "registration-390.png")):
        source = Path(item["screenshotPath"])
        if not source.exists():
            raise FileNotFoundError(source)
        shutil.copy2(source, auth_dir / name)

    scans = list(payload.get("scannedPages") or [])[:4]
    scans.extend([
        {"page_name": "Connexion", "page_url": login, "title": "Public login form", "type": "AUTH PAGE", "screenshot_path": str(auth_dir / "login-1440.png")},
        {"page_name": "Créer un compte consultant", "page_url": registration, "title": "Public consultant registration form", "type": "AUTH PAGE", "screenshot_path": str(auth_dir / "registration-1440.png")},
    ])
    payload["scannedPages"] = scans

    axes = {axis["id"]: axis for axis in payload.get("axes") or []}
    ui = axes["ui_consistency"]
    accessibility = axes["trust_accessibility"]
    task = axes["task_execution"]
    content = axes["content_microcopy"]

    mobile_evidence = (
        "The public auth forms retain the desktop split layout at 390px. Login has 323px horizontal overflow with 13 visible elements outside the viewport; "
        "registration has 326px overflow with 16 visible elements outside the viewport. The same failure remains at 430px (283px and 286px respectively)."
    )
    for item in ui.get("painPoints") or []:
        if "outside the phone viewport" in str(item.get("title", "")).lower():
            item["evidence"] = f"{item.get('evidence', '')} Additional public-auth evidence: {mobile_evidence}"
            item["explanation"] = item["evidence"]
            item["evidenceBundle"] = {
                "workspace": item.get("evidenceBundle"),
                "publicAuth": {"login390OverflowPx": 323, "registration390OverflowPx": 326, "login390OutsideControls": 13, "registration390OutsideControls": 16},
            }
            break
    ui["summary"] = "Hierarchy & Consistency is 86.5/100 across the accepted workspace evidence plus the two measured public auth pages. The responsive mobile finding is confirmed in both scopes."

    password_finding = finding(
        axis_id="trust_accessibility", axis_name="Accessibility",
        title="Password visibility controls are unnamed and too small for reliable access",
        severity="high", page_name="Connexion and Créer un compte consultant", page_url=login,
        evidence="Axe confirmed button-name and target-size failures on the password visibility controls: the eye buttons have no discernible accessible name and render at 16 × 16px, below the 24px minimum target size. Login has one affected control; registration has two. The results repeat at desktop and 390px.",
        why="People using screen readers cannot identify the control, and people with touch or motor impairments have an unnecessarily small activation target.",
        recommendation="Give every password visibility toggle an explicit localized accessible name that changes with state (for example, ‘Afficher le mot de passe’ / ‘Masquer le mot de passe’), expose its pressed state, and provide a minimum 24 × 24px hit target.",
        screenshot=auth_dir / "registration-1440.png", annotation="password-control",
        bundle={"source": "axe-core 4.11.1", "rules": ["button-name", "target-size"], "loginAffectedControls": 1, "registrationAffectedControls": 2, "controlSizePx": [16, 16]},
    )
    accessibility["painPoints"] = [password_finding, *(accessibility.get("painPoints") or [])]
    # The two distinct measured Axe rule families add two failed accessibility
    # rules to the accepted baseline (two passing / one failing): 2/5 passes.
    accessibility["score"] = 40.0
    accessibility["severity"] = "high"
    accessibility["summary"] = "Accessibility is 40/100 after adding the measured public-auth evidence. Existing workspace contrast failures remain, and the auth password controls add two distinct automated WCAG failures."
    accessibility.setdefault("signals", {}).update({"measuredRules": 5, "applicableRules": 6, "wcagFindings": "color-contrast; button-name; target-size"})

    form_finding = finding(
        axis_id="task_execution", axis_name="Task & Interaction",
        title="Required registration fields are not communicated before input",
        severity="medium", page_name="Créer un compte consultant", page_url=registration,
        evidence="All five registration inputs are natively required, but the observed labels provide neither a field-level required indicator nor a form-level statement that all fields are mandatory. The empty submit state is disabled, so no server-side submission was attempted.",
        why="People may not understand the completion requirement until the CTA remains unavailable, increasing avoidable form friction.",
        recommendation="Mark required fields consistently and add a concise form-level statement such as ‘Tous les champs sont obligatoires’; keep the requirement visible before users begin entering data.",
        screenshot=auth_dir / "registration-1440.png", annotation="required-fields",
        bundle={"source": "rendered DOM", "requiredInputCount": 5, "fieldLevelIndicator": False, "formLevelStatement": False, "submission": "not attempted"},
    )
    task["painPoints"] = [*(task.get("painPoints") or []), form_finding]
    task["summary"] = "Task & Interaction is 60/100 in the accepted workspace evidence plus the bounded public-auth form review. The registration form guidance issue is confirmed; error recovery was not exercised with credentials."

    for item in content.get("painPoints") or []:
        if "mixed french and english" in str(item.get("title", "")).lower():
            item["evidence"] = f"{item.get('evidence', '')} Public auth pages add visible product terminology including ‘Propales Intelligentes’ and ‘EY_PORPALEAI’; ‘propale/propales’ is treated as grammatical product usage, while the technical-looking product label should be standardized through product naming governance."
            item["explanation"] = item["evidence"]
            break

    existing = list(payload.get("executiveSummary", {}).get("topPriorities") or [])
    existing[0]["evidence"] = f"{existing[0].get('evidence', '')} Additional public-auth evidence: {mobile_evidence}"
    existing[0]["explanation"] = existing[0]["evidence"]
    existing.extend([password_finding, form_finding])
    summary = payload.setdefault("executiveSummary", {})
    summary["topPriorities"] = existing
    summary["overallScore"] = 75.6
    summary["summary"] = "The accepted authenticated-workspace audit has been extended with Login and Registration. The internal score is 75.6/100 (7.6/10 stakeholder display); the measured public auth password-control failures change Accessibility from 66.7 to 40.0."
    summary["criticalFindingCount"] = 0
    summary["hasCriticalBlocker"] = False
    summary["overallRating"] = "Measured"
    payload.setdefault("context", {})["pagesAudited"] = 6
    payload["scopeLimitations"] = [
        "Authenticated workspace coverage remains bounded to the accepted evidence set; it was not recollected for this extension.",
        "Login and Registration are additional public auth pages. Modal states are visual states, not independent routes.",
        "No credentials were entered, no account was created, and all state-changing requests were blocked during the public auth review.",
    ]
    payload["recommendations"] = [*list(payload.get("recommendations") or []), {
        "priority": "Critical", "title": password_finding["title"], "description": password_finding["recommendation"], "impact": password_finding["whyItMatters"], "axis": "Accessibility",
    }, {
        "priority": "High", "title": form_finding["title"], "description": form_finding["recommendation"], "impact": form_finding["whyItMatters"], "axis": "Task & Interaction",
    }]
    atomic_write_json(payload_path, payload)
    print(f"Updated stakeholder payload: {payload_path}")


if __name__ == "__main__":
    main()
