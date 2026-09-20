import http.server
import threading

import pytest

from app.services.scanning.scanner import run_scan
from app.services.scanning.ssrf_guard import ScanTargetError, validate_scan_target


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/.env"):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"SECRET=1")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body>hello</body></html>")

    def log_message(self, format, *args):  # noqa: A002
        pass


@pytest.fixture(scope="module")
def local_server():
    server = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


def test_ssrf_guard_rejects_unauthorized_host():
    with pytest.raises(ScanTargetError):
        validate_scan_target("http://example.com")


def test_ssrf_guard_rejects_non_http_scheme():
    with pytest.raises(ScanTargetError):
        validate_scan_target("file:///etc/passwd")


def test_ssrf_guard_allows_localhost():
    assert validate_scan_target("http://127.0.0.1:9999/") == "http://127.0.0.1:9999/"


def test_scan_finds_missing_security_headers_and_sensitive_path(local_server):
    outcome = run_scan(local_server)
    assert outcome.error is None
    assert "security_headers" in outcome.checks_run
    assert any("Content-Security-Policy" in f.finding for f in outcome.findings)
    assert any(f.owasp_category == "A01:2021" for f in outcome.findings)  # sensitive .env path


def test_scan_rejects_unauthorized_target():
    outcome = run_scan("http://example.com")
    assert outcome.error is not None
    assert outcome.findings == []
