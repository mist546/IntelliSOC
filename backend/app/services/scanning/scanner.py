import httpx

from app.config import get_settings
from app.services.scanning.base import ScanFinding, ScanOutcome
from app.services.scanning.checks import (
    check_cleartext_transport,
    check_cookies,
    check_reflected_xss,
    check_security_headers,
    check_sensitive_paths,
    check_server_banner,
    check_sql_error_disclosure,
)
from app.services.scanning.ssrf_guard import ScanTargetError, validate_scan_target
from app.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def run_scan(target_url: str) -> ScanOutcome:
    outcome = ScanOutcome()

    try:
        validated_url = validate_scan_target(target_url)
    except ScanTargetError as exc:
        outcome.error = str(exc)
        return outcome

    try:
        with httpx.Client(follow_redirects=False, timeout=settings.SCAN_TIMEOUT_SECONDS) as client:
            resp = client.get(validated_url)
    except httpx.HTTPError as exc:
        outcome.error = f"Could not reach target: {exc}"
        return outcome

    checks: list[tuple[str, list[ScanFinding]]] = [
        ("security_headers", check_security_headers(resp.headers, validated_url)),
        ("server_banner", check_server_banner(resp.headers, validated_url)),
        ("cleartext_transport", check_cleartext_transport(validated_url)),
        ("cookie_flags", check_cookies(resp, validated_url)),
    ]

    with httpx.Client(follow_redirects=False, timeout=settings.SCAN_TIMEOUT_SECONDS) as client:
        checks.append(("sensitive_paths", check_sensitive_paths(client, validated_url)))
        checks.append(("reflected_xss_probe", check_reflected_xss(client, validated_url)))
        checks.append(("sql_error_disclosure_probe", check_sql_error_disclosure(client, validated_url)))

    for name, findings in checks:
        outcome.checks_run.append(name)
        outcome.findings.extend(findings)

    logger.info("Scan of %s completed: %d finding(s) across %d check(s)", validated_url, len(outcome.findings), len(outcome.checks_run))
    return outcome
