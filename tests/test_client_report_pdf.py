"""The PDF is printed from the same client report HTML, with a client-ready filename."""
import re

from client_report_fixtures import REVISION, machine
from src.report.client import pdf
from src.report.client.context import build_client_report_context
from src.report.client.render import render_client_report
from test_client_report_routes import seeded
from test_server_security import api_server, request  # noqa: F401


def test_render_pdf_prints_a_multi_page_a4_document():
    context = build_client_report_context(audit_id="a", machine=machine(), revision=REVISION, audit_date="2026-10-06")
    document = pdf.render_pdf(render_client_report(context))
    assert document.startswith(b"%PDF")
    assert len(re.findall(rb"/Type\s*/Page[^s]", document)) >= 3


def test_pdf_filename_is_a_safe_slug():
    assert pdf.pdf_filename("Managers.tn / <Home>", "2026-10-06") == "managers-tn-home-ux-audit-2026-10-06.pdf"
    assert pdf.pdf_filename("", "2026-10-06") == "audit-ux-audit-2026-10-06.pdf"


def test_owner_downloads_the_pdf(api_server, monkeypatch):
    job_id = seeded(api_server)
    monkeypatch.setattr(pdf, "render_pdf", lambda html, **_: b"%PDF-1.7 fake")
    status, headers, body = request(api_server, "GET", f"/api/audits/{job_id}/client-report.pdf", token="token-a")
    assert status == 200 and body == b"%PDF-1.7 fake" and headers["Content-Type"] == "application/pdf"
    assert re.fullmatch(r'attachment; filename="[a-z0-9-]+-ux-audit-\d{4}-\d{2}-\d{2}\.pdf"', headers["Content-Disposition"])


def test_other_owner_cannot_download_the_pdf(api_server, monkeypatch):
    job_id = seeded(api_server)
    monkeypatch.setattr(pdf, "render_pdf", lambda html, **_: b"%PDF")
    assert request(api_server, "GET", f"/api/audits/{job_id}/client-report.pdf", token="token-b")[0] == 404


def test_pdf_failure_is_reported_without_details(api_server, monkeypatch):
    job_id = seeded(api_server)

    def broken(html, **_):
        raise pdf.PdfExportError("chromium missing at C:/secret/path")

    monkeypatch.setattr(pdf, "render_pdf", broken)
    status, _, body = request(api_server, "GET", f"/api/audits/{job_id}/client-report.pdf", token="token-a")
    assert status == 503 and b"PDF export is temporarily unavailable." in body and b"secret" not in body
