"""Apply the approved offline scoring and copy correction to a finished audit.

This script never opens a browser or recomputes collection results. It records a
single methodology cap for verified mobile task inaccessibility and rewrites only
stakeholder-facing copy using the evidence already stored in the audit payload.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.audit.workspace import atomic_write_json


COPY = {
    "Workspace action controls extend outside the phone viewport": {
        "explanation": "At 390px, core workspace controls extend beyond the viewport. The desktop sidebar leaves too little usable width for the action area.",
        "whyItMatters": "Mobile users can lose access to actions needed to manage an RFP.",
        "recommendation": "Collapse the sidebar at phone breakpoints. Stack or group card actions, and verify every control stays inside a 390px viewport.",
        "evidence": "Measured at 390px: 20 action-button instances extend outside the viewport across the accepted mobile evidence.",
    },
    "Error states do not explain the failure or provide a recovery path": {
        "explanation": "The AI-analysis dialog shows ERROR and unavailable values, but does not explain the failure or tell the user what to do next.",
        "whyItMatters": "Users cannot recover confidently and may abandon the proposal workflow.",
        "recommendation": "State what failed, identify unavailable data, and offer Retry, replace document, or support actions.",
        "evidence": "Observed: ERROR status, unavailable fields, and no visible recovery instruction.",
    },
    "Elements must meet minimum color contrast ratio thresholds": {
        "explanation": "Axe found eight low-contrast nodes in the workspace, including muted sidebar text and red or green status labels.",
        "whyItMatters": "Low-vision users may not be able to read status, utility text, or controls reliably.",
        "recommendation": "Update the affected text and status tokens to meet 4.5:1. Recheck all error, success, and muted-text variants with Axe.",
        "evidence": "Axe: 8 affected nodes; measured ratios range from 2.72:1 to 4.24:1 where 4.5:1 is required.",
    },
    "Mixed French and English interface labels reduce language consistency": {
        "explanation": "French workspace labels appear beside English labels such as Search by TDR name..., Success, Failed, ERROR, and SUCCESS.",
        "whyItMatters": "Mixed language makes filtering and status messages harder to scan for French-speaking users.",
        "recommendation": "Localize search, filter, and status labels consistently. Keep TDR only where it is an established business acronym.",
        "evidence": "Observed in the Appels d'offres workspace alongside Filtrer les TDR, En attente, En traitement, and Ignorés.",
    },
    "Password visibility controls are unnamed and too small for reliable access": {
        "explanation": "Password visibility buttons have no accessible name and render at 16 × 16px on login and registration.",
        "whyItMatters": "Screen-reader and touch users cannot reliably identify or activate the control.",
        "recommendation": "Add localized show/hide-password names, expose pressed state, and provide a 24 × 24px minimum target.",
        "evidence": "Axe confirmed button-name and target-size failures: one login control and two registration controls.",
    },
    "Required registration fields are not communicated before input": {
        "explanation": "All five registration fields are required, but the form gives no field-level cue or form-level statement before entry begins.",
        "whyItMatters": "Users may not understand why the submit action remains unavailable.",
        "recommendation": "Mark required fields consistently and add a short form-level statement before the first input.",
        "evidence": "Rendered DOM: 5 required inputs; no field-level indicator and no form-level required-fields statement.",
    },
}

COMPONENTS = [
    "Muted sidebar text (.pt-5)",
    "Muted sidebar text (.text-white/40)",
    "Secondary workspace label",
    "Error status text",
    "Error status text",
]


def walk(value: object) -> None:
    if isinstance(value, dict):
        title = value.get("title")
        if title in COPY:
            value.update(COPY[title])
            if title == "Elements must meet minimum color contrast ratio thresholds":
                for index, row in enumerate(value.get("contrastSamples") or []):
                    if index < len(COMPONENTS):
                        row["component"] = COMPONENTS[index]
        for child in value.values():
            walk(child)
    elif isinstance(value, list):
        for child in value:
            walk(child)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", required=True)
    args = parser.parse_args()
    path = Path(args.payload).resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    axes = {axis["id"]: axis for axis in payload.get("axes") or []}
    previous = {axis_id: float(axis["score"]) for axis_id, axis in axes.items()}

    # One root cause, one numeric consequence: the verified out-of-viewport
    # actions gate task completion rather than being also deducted from UI.
    task = axes["task_execution"]
    task["score"] = 40.0
    task["severity"] = "high"
    task["summary"] = "Task & Interaction is capped at 40/100 because verified core workspace actions extend outside the 390px viewport; the same root cause is not scored again in Hierarchy & Consistency."
    task.setdefault("signals", {})["scoreCeiling"] = 40.0
    task["signals"]["scoreCeilingReasons"] = ["Verified core action controls inaccessible at a supported 390px viewport."]
    axes["ui_consistency"]["summary"] = "Hierarchy & Consistency remains 86.5/100. Its responsive-layout evidence is documented here, while its task-completion consequence is scored once in Task & Interaction."

    revised = {axis_id: float(axis["score"]) for axis_id, axis in axes.items()}
    overall = round(sum(revised.values()) / len(revised), 1)
    summary = payload.setdefault("executiveSummary", {})
    summary["overallScore"] = overall
    summary["summary"] = f"The evidence-led score is {overall:.1f}/100 ({overall / 10:.1f}/10). The verified 390px task-access failure applies a Task & Interaction completion cap; no root cause is counted twice."
    payload["scoringReview"] = {
        "method": "Existing equal-weight five-axis mean with one task-completion cap.",
        "previousOverall": 75.6,
        "revisedOverall": overall,
        "changes": [{
            "criterion": "Core task actions remain accessible at supported mobile widths",
            "previousOutcome": "No task-completion cap applied",
            "revisedOutcome": "Fail; axis capped at 40/100",
            "weight": "Task & Interaction axis; one root-cause consequence",
            "evidence": "20 action-button instances extend outside the 390px viewport in accepted mobile evidence.",
            "axis": "Task & Interaction",
            "impact": -20.0,
        }],
        "reassessedUnchanged": [
            "IA & Navigation: no confirmed architecture failure.",
            "Accessibility: remains 40/100 from three measured WCAG rule families.",
            "Hierarchy & Consistency: responsive root cause documented but not numerically duplicated.",
            "Content & Guidance: 11 measured passes and one confirmed language-consistency failure retain 91.7/100.",
        ],
        "axisPrevious": previous,
        "axisRevised": revised,
    }
    walk(payload)
    atomic_write_json(path, payload)
    print(f"Corrected stakeholder payload: {path}")


if __name__ == "__main__":
    main()
