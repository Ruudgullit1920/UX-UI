"""Render the client report context as one self-contained, script-free HTML document (screen + A4 print)."""
from __future__ import annotations

import datetime as _dt
import html
from pathlib import Path
from typing import Any

from src.gtm_audit.generate_gtm_report import ey_studio_logo_svg
from src.report.client.charts import SEVERITY_COLOURS, axis_bars, score_gauge, severity_donut
from src.report.roadmap_teaser import CHIP_LABELS, teaser_payload

STYLES = Path(__file__).with_name("styles.css").read_text(encoding="utf-8")
FONTS = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
SEVERITY_LABELS = {"critical": "Critical", "high": "High", "medium": "Medium", "low": "Low"}
INSIGHTS = [("strengths", "Strength areas", "good"), ("improvements", "Critical improvement areas", "critical"),
            ("opportunities", "Other opportunities", "info"), ("recommendations", "Recommendations", "accent")]
ROADMAP = [("now", "Now", "Critical and high-impact fixes"), ("next", "Next", "Medium-impact improvements"), ("later", "Later", "Polish and refinements")]


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _p(value: Any, cls: str = "") -> str:
    if not value:
        return ""
    attr = f' class="{cls}"' if cls else ""
    return f"<p{attr}>{esc(value)}</p>"


def _link(url: Any, text: Any) -> str:
    url = str(url or "")
    return f'<a href="{esc(url)}">{esc(text)}</a>' if url.startswith(("https://", "http://")) else esc(text)


def _date(value: str) -> str:
    try:
        day = _dt.date.fromisoformat(value[:10])
        return f"{day.day} {day:%B %Y}"
    except (TypeError, ValueError):
        return esc(value)


def _pill(severity: str) -> str:
    colour = SEVERITY_COLOURS.get(severity, SEVERITY_COLOURS["low"])
    return f'<span class="pill pill-{esc(severity)}"><span class="dot" style="background:{colour}"></span>{SEVERITY_LABELS.get(severity, "Low")}</span>'


def _tag(text: Any) -> str:
    return f'<span class="tag">{esc(text)}</span>' if text else ""


def _section(section_id: str, number: str, title: str, body: str, *, lead: str = "") -> str:
    return (f'<section id="{section_id}" class="section" aria-labelledby="{section_id}-title"><header class="section-head">'
            f'<span class="section-number">{number}</span><h2 id="{section_id}-title">{esc(title)}</h2>{_p(lead, "section-lead")}</header>{body}</section>')


def _cover(c: dict[str, Any]) -> str:
    overall = c["overall"]
    url = f'<p class="cover-url">{_link(c["site"]["url"], c["site"]["url"])}</p>' if c["site"]["url"] else ""
    return (f'<section id="cover" class="cover"><div class="cover-top">{ey_studio_logo_svg("cover-logo")}<span class="confidential">Confidential · Client deliverable</span></div>'
            f'<div class="cover-body"><div class="cover-text"><p class="eyebrow">UX/UI Audit Report</p><h1>{esc(c["site"]["name"])}</h1>{url}'
            f'<dl class="cover-meta"><div><dt>Audit date</dt><dd>{_date(c["auditDate"])}</dd></div><div><dt>Status</dt><dd>{esc(c["review"]["label"])}</dd></div></dl></div>'
            f'<div class="cover-score">{score_gauge(overall["score"], label="Overall UX score", size=220)}<p class="cover-score-label">Overall UX score</p>{_p(overall["rating"], "cover-rating")}</div></div>'
            f'<p class="cover-foot">Prepared by EY Studio+ · Evidence-based assessment of usability, accessibility, navigation, visual hierarchy and content.</p></section>')


def _kpi(value: str, label: str, note: str = "", tone: str = "") -> str:
    return f'<div class="kpi {tone}"><p class="kpi-value">{value}</p><p class="kpi-label">{esc(label)}</p>{_p(note, "kpi-note")}</div>'


def _executive(c: dict[str, Any]) -> str:
    score, k = c["overall"]["score"], c["kpis"]
    tiles = (_kpi("—" if score is None else f"{round(score)}<small>/100</small>", "Overall UX score", c["overall"]["rating"])
             + _kpi(str(k["pagesAudited"]), "Pages audited") + _kpi(str(k["findings"]), "Findings to address")
             + _kpi(str(k["critical"]), "Critical issues", "Blocking issues present" if k["blockers"] else "No blocking issues", "kpi-alert" if k["critical"] else ""))
    items = "".join(f'<li class="priority"><span class="priority-index">{i}</span><div><div class="meta-row">{_pill(p["severity"])}{_tag(p["axis"])}</div>'
                    f'<h3>{esc(p["title"])}</h3>{_p(p["recommendation"])}</div></li>' for i, p in enumerate(c["topPriorities"], 1))
    top = f'<h3 class="sub-head">Top priorities</h3><ol class="priorities">{items}</ol>' if items else ""
    return _section("executive-summary", "01", "Executive summary", f'<div class="kpis">{tiles}</div>{_p(c["positioningHook"], "lead")}{top}')


def _scorecard(c: dict[str, Any]) -> str:
    if not c["axes"] and not c["kpis"]["findings"]:
        return ""
    legend = "".join(f'<li><span class="dot" style="background:{SEVERITY_COLOURS[s]}"></span>{SEVERITY_LABELS[s]}<strong>{c["severityCounts"][s]}</strong></li>' for s in SEVERITY_COLOURS)
    callouts = "".join(f'<div class="callout callout-{tone}"><p class="callout-label">{label}</p><p class="callout-value">{esc(value)}</p></div>'
                       for tone, label, value in (("good", "Strongest area", c["strongestAxis"]), ("critical", "Weakest area", c["weakestAxis"])) if value)
    bars = f'<div class="card"><h3 class="card-title">Score by audit area</h3>{axis_bars(c["axes"])}<p class="scale">0–49 needs attention · 50–69 fair · 70–100 strong</p></div>' if c["axes"] else ""
    donut = f'<div class="card donut-card"><h3 class="card-title">Findings by severity</h3><div class="donut-wrap">{severity_donut(c["severityCounts"])}<ul class="legend">{legend}</ul></div></div>'
    callouts = f'<div class="callouts">{callouts}</div>' if callouts else ""
    body = f'<div class="score-grid">{bars}{donut}</div>{callouts}'
    return _section("scorecard", "02", "Scorecard", body, lead="How the experience performs across the five audit areas.")


def _insights(c: dict[str, Any]) -> str:
    panels = "".join(f'<div class="panel panel-{tone}"><h3>{label}</h3><ul>{"".join(f"<li>{esc(item)}</li>" for item in c["insights"][key])}</ul></div>'
                     for key, label, tone in INSIGHTS if c["insights"][key])
    return _section("insights", "03", "Key insights", f'<div class="panels">{panels}</div>') if panels else ""


def _finding(f: dict[str, Any], images: dict[str, str]) -> str:
    image = images.get(f["key"], "")
    figure = (f'<figure class="evidence"><img src="{esc(image)}" alt="Highlighted section of the page for: {esc(f["title"])}"/>'
              f'<figcaption>{esc(f["pageName"] or "Captured page")}</figcaption></figure>') if image.startswith("data:image/") else ""
    blocks = "".join(f'<div class="block block-{cls}"><h4>{label}</h4>{_p(text)}</div>'
                     for cls, label, text in (("problem", "The problem", f["problem"]), ("why", "Why it matters", f["whyItMatters"]), ("fix", "Recommendation", f["recommendation"])) if text)
    review = "".join(_p(text, "review-note") for text in (f"Reviewer priority: {f['reviewerPriority']}" if f["reviewerPriority"] else "",
                                                        f"Reviewer note: {f['reviewerNote']}" if f["reviewerNote"] else ""))
    ai = '<span class="tag tag-ai">Identified by the AI agent</span>' if f["aiDiscovered"] else ""
    page = f'<span class="page">{_link(f["pageUrl"], f["pageName"] or f["pageUrl"])}</span>' if (f["pageName"] or f["pageUrl"]) else ""
    return (f'<article class="finding-card{" has-image" if figure else ""}"><div class="meta-row">{_pill(f["severity"])}{_tag(f["axis"])}{ai}{page}</div>'
            f'<h3>{esc(f["title"])}</h3><div class="finding-body">{figure}<div class="finding-text">{blocks}{review}</div></div></article>')


def _findings(c: dict[str, Any], images: dict[str, str]) -> str:
    if not c["findings"]:
        return ""
    groups = []
    for severity in SEVERITY_LABELS:
        cards = [_finding(f, images) for f in c["findings"] if f["severity"] == severity]
        if cards:
            groups.append(f'<div class="finding-group"><h3 class="group-head">{_pill(severity)}<span>{len(cards)} finding{"s" if len(cards) != 1 else ""}</span></h3>{"".join(cards)}</div>')
    lead = f'{len(c["findings"])} findings, ordered by severity. Each one shows the affected section, the problem and the recommended fix.'
    return _section("findings", "04", "Detailed findings", "".join(groups), lead=lead)


def _roadmap(c: dict[str, Any]) -> str:
    if not any(c["roadmap"].values()):
        return ""
    columns = "".join(f'<div class="lane lane-{key}"><h3>{label}</h3><p class="lane-note">{note}</p><ol>'
                      + "".join(f'<li><strong>{esc(item["title"])}</strong>{_p(item["description"])}{_tag(item["axis"])}</li>' for item in c["roadmap"][key])
                      + "</ol></div>" for key, label, note in ROADMAP if c["roadmap"][key])
    return _section("roadmap", "05", "Improvement roadmap", f'<div class="lanes">{columns}</div>', lead="Recommended sequence, from highest to lowest impact.")


def _next_steps(c: dict[str, Any]) -> str:
    payload = teaser_payload(c["findings"], lang=c["language"], site_url=c["site"]["url"], report_url=None)
    if not payload or not str(payload.get("bookingUrl", "")).startswith("https://"):
        return ""
    copy, expert = payload["copy"], payload["expert"]
    heading = copy["heading"] if c["findings"] else copy["cleanHeading"]
    body = copy["body"] if c["findings"] else copy["cleanBody"]
    counts = payload.get("counts") or {}
    chips = "".join(f'<li><strong>{counts[key]}</strong> {esc(copy[one] if counts[key] == 1 else copy[key])}</li>'
                    for key, one in CHIP_LABELS if counts.get(key) and key in copy and one in copy)
    chips = f'<ul class="cta-chips">{chips}</ul>' if chips else ""
    return (f'<section id="next-steps" class="cta"><div><p class="eyebrow">{esc(copy["eyebrow"])}</p><h2>{esc(heading)}</h2>{_p(body)}{chips}'
            f'<p class="cta-expert"><strong>{esc(expert["name"])}</strong> · {esc(expert["title"])}</p></div>'
            f'<a class="cta-button" href="{esc(payload["bookingUrl"])}">{esc(copy["cta"])} →</a></section>')


def _appendix(c: dict[str, Any]) -> str:
    a = c["appendix"]
    listing = lambda items: "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"  # noqa: E731
    pages = "<ul>" + "".join(f'<li>{_link(p["url"], p["name"] or p["url"])}</li>' for p in a["coverage"]) + "</ul>" if a["coverage"] else ""
    rows = "".join(f'<tr><td>{esc(f["title"])}</td><td>{esc(f["provenance"]["source"])}</td><td>{esc(f["provenance"]["criterion"])}</td>'
                   f'<td><code>{esc(f["provenance"]["selector"])}</code></td><td>{esc(f["provenance"]["measurementClass"])}</td></tr>' for f in c["findings"])
    table = (f'<h3 class="sub-head">Evidence provenance</h3><table class="provenance"><thead><tr><th>Finding</th><th>Source</th><th>Criterion</th>'
             f'<th>Element</th><th>Measurement</th></tr></thead><tbody>{rows}</tbody></table>') if rows else ""
    excluded = ('<h3 class="sub-head">Excluded by reviewer</h3><ul>' + "".join(f'<li><strong>{esc(e["title"])}</strong>{" — " + esc(e["reason"]) if e["reason"] else ""}</li>' for e in c["excluded"]) + "</ul>") if c["excluded"] else ""
    body = (f'<div class="appendix-grid"><div><h3 class="sub-head">Methodology</h3>{listing(a["methodology"])}</div>'
            f'<div><h3 class="sub-head">Pages audited</h3>{pages or "<p>Not recorded.</p>"}</div>'
            f'<div><h3 class="sub-head">Limitations</h3>{listing(a["limitations"])}</div></div>{table}{excluded}')
    return _section("appendix", "06", "Appendix", body)


def render_client_report(context: dict[str, Any], images: dict[str, str] | None = None) -> str:
    images = {k: v for k, v in (images or {}).items() if isinstance(v, str) and v.startswith("data:image/")}
    lang = esc((context.get("language") or "en").split("-")[0])
    title = f'{context["site"]["name"]} — UX/UI Audit Report'
    body = (_cover(context) + _executive(context) + _scorecard(context) + _insights(context)
            + _findings(context, images) + _roadmap(context) + _next_steps(context) + _appendix(context))
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{esc(title)}</title><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="{FONTS}">'
            f'<style>{STYLES}</style></head><body><main class="report">{body}</main></body></html>')
