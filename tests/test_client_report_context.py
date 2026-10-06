"""The client report context turns audit data plus review edits into presentation-ready facts."""
import copy
import json

from client_report_fixtures import REVISION, machine
from src.report.client.context import build_client_report_context


def build(data=None, revision=REVISION, **kwargs):
    return build_client_report_context(audit_id="audit-1", machine=machine() if data is None else data, revision=revision, **kwargs)


def test_kpis_count_visible_findings_and_pages():
    context = build()
    assert context["kpis"] == {"pagesAudited": 2, "findings": 4, "critical": 1, "blockers": True}
    assert context["overall"]["score"] == 60.2 and context["overall"]["rating"] == "Measured"


def test_site_name_uses_the_domain_not_the_page_title():
    assert build()["site"] == {"name": "managers.tn", "url": "https://managers.tn/"}


def test_severity_counts_apply_reviewer_priority_override():
    assert build()["severityCounts"] == {"critical": 1, "high": 0, "medium": 2, "low": 1}


def test_axis_bands_follow_score_thresholds():
    bands = {axis["name"]: axis["band"] for axis in build()["axes"]}
    assert bands == {"Task & Interaction": "green", "IA & Navigation": "red", "Accessibility": "red",
                     "Hierarchy & Consistency": "amber", "Content & Guidance": "none"}


def test_suppressed_findings_move_to_excluded_with_reason():
    context = build()
    assert "Duplicate finding" not in [f["title"] for f in context["findings"]]
    assert context["excluded"] == [{"title": "Duplicate finding", "reason": "Duplicate of d2"}]


def test_reviewer_edits_override_machine_text():
    first = build()["findings"][0]
    assert first["key"] == "d1" and first["severity"] == "critical"
    assert first["recommendation"] == "Give every icon button an accessible name."
    assert first["reviewerNote"] == "Confirmed on mobile too" and first["reviewerPriority"] == "critical"


def test_findings_sorted_by_severity_and_ai_findings_keyed():
    findings = build()["findings"]
    assert [f["severity"] for f in findings] == ["critical", "medium", "medium", "low"]
    ai = [f for f in findings if f["aiDiscovered"]]
    assert [f["key"] for f in ai] == ["ai-0", "ai-1"]
    assert ai[0]["problem"] == "Empty thumbnails." and ai[0]["whyItMatters"] == "Looks broken."


def test_ai_finding_already_in_deduplicated_list_is_not_repeated():
    data = machine()
    data["aiDiscoveredFindings"].append({"title": "Links rely on colour", "pageUrl": "https://managers.tn/", "aiDiscovered": True})
    assert [f["title"] for f in build(data)["findings"]].count("Links rely on colour") == 1


def test_roadmap_buckets_by_priority():
    roadmap = build()["roadmap"]
    assert [item["title"] for item in roadmap["now"]] == ["Label icon buttons"]
    assert [item["title"] for item in roadmap["next"]] == ["Unify nav language"]
    assert [item["title"] for item in roadmap["later"]] == ["Trim homepage"]


def test_insights_take_titles_and_cap_at_four():
    insights = build()["insights"]
    assert insights["strengths"][0] == "Task & Interaction strength"
    assert all(len(items) <= 4 for items in insights.values())
    assert insights["recommendations"][0] == "Label icon buttons"


def test_top_priorities_and_strongest_weakest_axes():
    context = build()
    assert context["topPriorities"][0]["title"] == "Buttons must have discernible text"
    assert context["strongestAxis"] == "Task & Interaction" and context["weakestAxis"] == "Accessibility"


def test_review_label_and_audit_date():
    context = build(audit_date="2026-10-06")
    assert context["auditDate"] == "2026-10-06" and context["review"]["status"] == "validated"
    assert build(revision=None)["review"]["label"] == "Automated audit — not yet reviewed"


def test_context_is_json_serialisable_and_input_untouched():
    data = machine()
    before = copy.deepcopy(data)
    json.dumps(build(data))
    assert data == before


def test_empty_machine_still_builds():
    context = build({}, revision=None)
    assert context["overall"]["score"] is None and context["findings"] == [] and context["axes"] == []
    assert context["kpis"] == {"pagesAudited": 0, "findings": 0, "critical": 0, "blockers": False}
