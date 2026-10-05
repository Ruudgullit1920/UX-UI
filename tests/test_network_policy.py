from __future__ import annotations

import asyncio
import os
import pytest

from src.security.network_policy import (
    UnsafeURLError,
    browser_request_is_allowed,
    fetch_public_text,
    install_playwright_network_guard,
    sanitize_audit_ssl_keylogfile,
    validate_dependency_origin,
    validate_public_url,
)
from conftest import FakeRequest, FakeRoute


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/file",
        "http://user:pass@example.com/",
        "http://127.0.0.1/",
        "http://127.1/",
        "http://0177.0.0.1/",
        "http://2130706433/",
        "http://0x7f000001/",
        "http://0x7f.0.0.1/",
        "http://%31%32%37.0.0.1/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://169.254.169.254/latest/meta-data/",
        "http://example.com:22/",
        "http://example.com\\@127.0.0.1/",
    ],
)
def test_rejects_unsafe_urls(url, public_resolver):
    with pytest.raises(UnsafeURLError):
        validate_public_url(url, resolver=public_resolver)


def test_normalizes_idn_and_trailing_dot(public_resolver):
    value = validate_public_url("https://EXAMPLE.com./a#fragment", resolver=public_resolver)
    assert value.url == "https://example.com/a"
    assert value.addresses == ("93.184.216.34",)


def test_mixed_public_private_dns_is_rejected():
    resolver = lambda _host, _port: ["93.184.216.34", "10.0.0.7"]
    with pytest.raises(UnsafeURLError):
        validate_public_url("https://example.com/", resolver=resolver)


def test_redirect_to_metadata_is_revalidated_and_blocked(monkeypatch, public_resolver):
    class Headers:
        @staticmethod
        def get_content_charset():
            return "utf-8"

    class Response:
        status = 302
        headers = Headers()

        @staticmethod
        def getheader(name):
            return "http://169.254.169.254/latest/meta-data/" if name == "Location" else None

        @staticmethod
        def read(_size):
            return b""

    class Connection:
        def __init__(self, *_args, **_kwargs):
            pass

        def request(self, *_args, **_kwargs):
            pass

        def getresponse(self):
            return Response()

        def close(self):
            pass

    monkeypatch.setattr("src.security.network_policy._PinnedHTTPSConnection", Connection)
    with pytest.raises(UnsafeURLError):
        fetch_public_text("https://example.com/", resolver=public_resolver)


def test_browser_guard_blocks_private_subrequest(monkeypatch, playwright_context, public_resolver):
    allowed = validate_public_url("https://example.com/", resolver=public_resolver)
    asyncio.run(install_playwright_network_guard(playwright_context, [allowed]))
    route = FakeRoute()
    asyncio.run(playwright_context.handler(route, FakeRequest("http://169.254.169.254/latest/meta-data/")))
    assert route.action == "abort"


def test_browser_guard_blocks_dns_rebinding(monkeypatch, playwright_context, public_resolver):
    allowed = validate_public_url("https://example.com/", resolver=public_resolver)
    monkeypatch.setattr("src.security.network_policy._system_resolver", lambda _host, _port: ["127.0.0.1"])
    asyncio.run(install_playwright_network_guard(playwright_context, [allowed]))
    route = FakeRoute()
    asyncio.run(playwright_context.handler(route, FakeRequest("https://example.com/api")))
    assert route.action == "abort"


def test_explicit_dependency_origin_is_required_for_authenticated_api_host():
    frontend = validate_public_url("http://4.209.241.167/")
    dependency = validate_dependency_origin("http://4.209.37.93/")

    assert not browser_request_is_allowed("http://4.209.37.93/auth/me", [frontend])
    assert browser_request_is_allowed("http://4.209.37.93/auth/me", [frontend, dependency])
    assert browser_request_is_allowed("http://4.209.37.93/projects", [frontend, dependency])


def test_explicit_dependency_does_not_authorize_other_origins_or_restricted_redirects():
    frontend = validate_public_url("http://4.209.241.167/")
    dependency = validate_dependency_origin("http://4.209.37.93/")

    assert not browser_request_is_allowed("http://1.1.1.1/", [frontend, dependency])
    assert not browser_request_is_allowed("http://169.254.169.254/latest/meta-data/", [frontend, dependency])
    assert not browser_request_is_allowed("https://4.209.37.93/auth/me", [frontend, dependency])


def test_normal_public_audit_origin_behavior_is_unchanged(public_resolver):
    homepage = validate_public_url("https://example.com/", resolver=public_resolver)

    assert browser_request_is_allowed("https://example.com/path", [homepage], resolver=public_resolver)
    with pytest.raises(UnsafeURLError):
        validate_dependency_origin("https://example.com/path", resolver=public_resolver)


def test_only_machine_injected_ssl_keylog_device_paths_are_sanitized(monkeypatch):
    monkeypatch.setenv("SSLKEYLOGFILE", r"\\.\avgMonFltProxy\audit")
    assert sanitize_audit_ssl_keylogfile()
    assert "SSLKEYLOGFILE" not in os.environ

    monkeypatch.setenv("SSLKEYLOGFILE", r"C:\audit\ssl-keys.log")
    assert not sanitize_audit_ssl_keylogfile()
