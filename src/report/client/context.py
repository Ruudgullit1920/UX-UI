"""Presentation-ready, JSON-serialisable facts for the client report. Pure: no I/O, never mutates input."""
from __future__ import annotations

import datetime as _dt
from urllib.parse import urlparse
from urllib.parse import urlparse
from typing import Any

from src.report.reviewed_report import reviewed_report_context
from src.report.roadmap_teaser import NON_FAILING

SEVERITIES = ("critical", "high", "medium", "low")
LIMITATIONS = [
    "Automated accessibility checks do not establish complete WCAG conformance.",
    "Performance figures are laboratory measurements, not field data from real visitors.",
    "AI interpretation of screenshots is probabilistic; contrast and focus order may need human confirmation.",
]
REVIEWED = {"validated", "approved"}
ROADMAP_LANE_LIMIT = 6


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(_text(item) for item in value if item)
    return "" if value is None else str(value).strip()


def _number(value: Any) -> float | None:
    try:
        return None if value is None or isinstance(value, bool) else float(value)
    except (TypeError, ValueError):
        return None


def _severity(value: Any) -> str:
    value = _text(value).lower()
    return value if value in SEVERITIES else "low"


def _band(score: float | None, scored: bool) -> str:
    if score is None or not scored:
        return "none"
    return "green" if score >= 70 else "amber" if score >= 50 else "red"


def _title(item: Any) -> str:
    return _text(item.get("title") if isinstance(item, dict) else item)


def _name(value: Any) -> str:
    return _text(value.get("name") or value.get("shortName")) if isinstance(value, dict) else _text(value)


def _identity(item: dict[str, Any]) -> str:
    return _text(item.get("findingId") or item.get("id") or item.get("deduplicationId"))


def _finding_record(item: dict[str, Any], key: str, ai: bool) -> dict[str, Any]:
    review = _dict(item.get("review"))
    override = _text(review.get("priorityOverride")).lower()
    bundle = _dict(item.get("evidenceBundle"))
    target = bundle.get("target")
    return {
        "key": key, "title": _text(item.get("title")) or "Untitled finding",
        "severity": override if override in SEVERITIES else _severity(item.get("severity")),
        "axis": _text(item.get("axisName") or item.get("sourceSheet")), "pageName": _text(item.get("pageName")), "pageUrl": _text(item.get("pageUrl")),
        "problem": _text(item.get("explanation")) or _text(item.get("evidence")), "whyItMatters": _text(item.get("whyItMatters")),
        "recommendation": _text(review.get("reviewedRecommendation")) or _text(item.get("recommendation")),
        "reviewerNote": _text(review.get("reviewNote")), "reviewerPriority": override if override in SEVERITIES else "",
        "aiDiscovered": ai, "screenshotPath": _text(item.get("screenshotPath")),
        "visualRegion": item.get("visualRegion") if isinstance(item.get("visualRegion"), dict) else None,
        "evidenceBundle": bundle or None,
        "provenance": {"source": _text(bundle.get("source") or item.get("measurementMethod") or ("AI agent" if ai else "")),
                       "criterion": _text(item.get("wcagCriterion") or bundle.get("criterion")),
                       "selector": _text(target.get("selector") if isinstance(target, dict) else target),
                       "measurementClass": _text(item.get("measurementClass")), "evidence": _text(item.get("evidence"))},
    }


def _findings(reviewed: dict[str, Any], machine: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    findings, excluded, defects = [], [], set()
    for index, item in enumerate(reviewed["completeFindings"]):
        defect = _text(item.get("deduplicationId"))
        if _text(item.get("outcome") or item.get("status")).lower() in NON_FAILING or (defect and defect in defects):
            continue
        defects.add(defect)
        review = _dict(item.get("review"))
        if review.get("suppressed"):
            excluded.append({"title": _text(item.get("title")) or "Untitled finding", "reason": _text(review.get("suppressionReason"))})
        else:
            findings.append(_finding_record(item, _identity(item) or f"f-{index}", bool(item.get("aiDiscovered"))))
    seen = {(f["title"], f["pageUrl"]) for f in findings} | {(e["title"], "") for e in excluded}
    for index, item in enumerate(_list(machine.get("aiDiscoveredFindings"))):
        if not isinstance(item, dict) or (_text(item.get("title")), _text(item.get("pageUrl"))) in seen:
            continue
        findings.append(_finding_record(item, _identity(item) or f"ai-{index}", True))
    findings.sort(key=lambda f: SEVERITIES.index(f["severity"]))
    return findings, excluded


def _capped(items: list[str], limit: int = 4) -> list[str]:
    out: list[str] = []
    for item in items:
        if item and item not in out:
            out.append(item)
    return out[:limit]


def _review(revision: dict[str, Any] | None, reviewed: dict[str, Any]) -> dict[str, Any]:
    status = _text((revision or {}).get("reviewStatus")) or "unreviewed"
    label = ("Automated audit — not reviewed" if status == "unreviewed"
             else "Reviewed and validated by EY Studio+" if status in REVIEWED else "Expert review in progress")
    return {"status": status, "label": label, "revisionId": reviewed.get("revisionId"), "reviewer": reviewed.get("reviewer") or {}}


def build_client_report_context(*, audit_id: str, machine: dict[str, Any], revision: dict[str, Any] | None, audit_date: str | None = None) -> dict[str, Any]:
    machine = _dict(machine)
    reviewed = reviewed_report_context(audit_id=audit_id, machine=machine, revision=revision)
    site = _dict(machine.get("site"))
    executive = _dict(machine.get("executiveSummary"))
    findings, excluded = _findings(reviewed, machine)
    counts = {severity: sum(1 for f in findings if f["severity"] == severity) for severity in SEVERITIES}
    axes = [{"id": _text(axis.get("id")), "name": _name(axis), "score": _number(axis.get("score")), "scored": axis.get("scored") is not False and _number(axis.get("score")) is not None,
             "summary": _text(axis.get("summary")), "_source": axis} for axis in _list(machine.get("axes")) if isinstance(axis, dict)]
    for axis in axes:
        axis["band"] = _band(axis["score"], axis["scored"])
    by_strength = sorted(axes, key=lambda a: -(a["score"] if a["scored"] else -1))
    by_weakness = sorted(axes, key=lambda a: a["score"] if a["scored"] else 101)
    recommendations = [r for r in _list(machine.get("recommendations")) if isinstance(r, dict)]
    roadmap: dict[str, list[dict[str, str]]] = {"now": [], "next": [], "later": []}
    for finding in findings:  # already ordered by severity
        bucket = "now" if finding["severity"] in {"critical", "high"} else "next" if finding["severity"] == "medium" else "later"
        if len(roadmap[bucket]) < ROADMAP_LANE_LIMIT:
            roadmap[bucket].append({"title": finding["title"], "description": finding["recommendation"], "axis": finding["axis"]})
    pages = [{"name": _text(p.get("page_name") or p.get("title")), "url": _text(p.get("page_url"))} for p in _list(machine.get("scannedPages")) if isinstance(p, dict)]
    methodology = [": ".join(x for x in (_text(m.get("step")), _text(m.get("description"))) if x) if isinstance(m, dict) else _text(m)
                   for m in _list(machine.get("methodology"))] or reviewed["methodology"]
    context = {
        "auditId": audit_id, "site": {"name": _text(site.get("domain")) or urlparse(_text(site.get("homepage") or site.get("url"))).netloc or "Audited site", "url": _text(site.get("homepage") or site.get("url"))},
        "language": _text(site.get("language") or machine.get("language")) or "en",
        "auditDate": audit_date or _dt.date.today().isoformat(), "review": _review(revision, reviewed),
        "overall": {"score": _number(executive.get("overallScore")), "rating": _text(executive.get("overallRating")), "reason": _text(executive.get("overallReason"))},
        "kpis": {"pagesAudited": len(pages), "findings": len(findings), "critical": counts["critical"],
                 "blockers": bool(executive.get("hasCriticalBlocker")) or counts["critical"] > 0},
        "positioningHook": _text(executive.get("positioningHook")),
        "topPriorities": [{"title": _title(p), "axis": _text(p.get("axisName") or p.get("sourceSheet")), "severity": _severity(p.get("severity")),
                           "recommendation": _text(p.get("recommendation"))} for p in reviewed["priorities"][:3] if isinstance(p, dict)],
        "axes": [{k: v for k, v in axis.items() if k != "_source"} for axis in axes],
        "severityCounts": counts,
        "strongestAxis": _name(executive.get("strongestAxis")), "weakestAxis": _name(executive.get("weakestAxis")),
        "insights": {"strengths": _capped([_title(s) for a in by_strength for s in _list(a["_source"].get("strengths"))]),
                     "improvements": _capped([_title(s) for a in by_weakness for s in _list(a["_source"].get("painPoints"))]),
                     "opportunities": _capped([_title(s) for a in by_weakness for s in _list(a["_source"].get("opportunities"))]),
                     "recommendations": _capped([_title(r) for r in recommendations])},
        "findings": findings, "excluded": excluded, "roadmap": roadmap,
        "appendix": {"methodology": methodology, "coverage": pages, "limitations": LIMITATIONS},
    }
    return context


def client_context_from_reviewed(reviewed: dict[str, Any]) -> dict[str, Any]:
    """Adapt a legacy reviewed-report context (review edits already merged) into a client context."""
    changes, findings = {}, []
    for item in _list(reviewed.get("completeFindings")):
        if not isinstance(item, dict):
            continue
        findings.append({k: v for k, v in item.items() if k != "review"})
        if _identity(item):
            changes[_identity(item)] = _dict(item.get("review"))
    machine = {"deduplicatedFindings": findings, "priorities": _list(reviewed.get("priorities")),
               "site": {"homepage": reviewed.get("siteUrl") or ""}, "language": reviewed.get("language") or "en"}
    revision = {"revisionId": reviewed.get("revisionId"), "reviewStatus": reviewed.get("reviewStatus") or "unreviewed", "changes": changes,
                **_dict(reviewed.get("reviewer"))}
    return build_client_report_context(audit_id=_text(reviewed.get("auditId")), machine=machine, revision=revision)
