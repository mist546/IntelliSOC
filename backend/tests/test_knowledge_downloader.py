"""Unit tests for the knowledge base downloader's converters (no network).

The download functions themselves need the internet; these tests cover the
pure conversion logic (KEV filtering/grouping, Sigma YAML -> markdown)
(the ATT&CK STIX conversion now lives in app/services/rag/loaders.py and is
tested in test_rag_loaders.py) on small inline fixtures.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "download_knowledge_base.py"


@pytest.fixture(scope="module")
def dl():
    spec = importlib.util.spec_from_file_location("download_knowledge_base", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["download_knowledge_base"] = module
    spec.loader.exec_module(module)
    return module


def _kev(cve, vendor, product, name, added="2026-01-01"):
    return {
        "cveID": cve,
        "vendorProject": vendor,
        "product": product,
        "vulnerabilityName": name,
        "dateAdded": added,
        "dueDate": "2026-01-22",
        "shortDescription": f"{product} contains a vulnerability.",
        "requiredAction": "Apply updates per vendor instructions.",
        "knownRansomwareCampaignUse": "Known",
    }


def test_kev_filters_by_keyword_and_groups_small_vendors(dl):
    vulns = [_kev(f"CVE-2026-{i:04d}", "Microsoft", "Windows", "Windows Elevation of Privilege") for i in range(6)]
    vulns += [
        _kev("CVE-2026-9001", "Apache", "HTTP Server", "Apache Path Traversal", added="2026-03-01"),
        _kev("CVE-2026-9002", "Zyxel", "Firewall", "Zyxel SQL Injection Vulnerability"),
        _kev("CVE-2026-9003", "Adobe", "Reader", "Adobe Reader Use-After-Free"),  # no keyword match
    ]
    docs = dl.kev_to_markdown(vulns, ["microsoft windows", "apache", "sql injection"])

    assert set(docs) == {"microsoft", "other_vendors"}
    assert docs["microsoft"].count("\n## CVE-2026-") == 6
    other = docs["other_vendors"]
    assert "CVE-2026-9001" in other and "CVE-2026-9002" in other
    assert "CVE-2026-9003" not in other
    # Entries keep their own vendor even inside the shared document, and carry the KEV facts.
    assert "Product: Apache HTTP Server." in other
    assert "Known ransomware campaign use: Known" in other
    assert "confirmed exploited in the wild" in other
    assert other.startswith("---\ntitle: CISA KEV")


def test_kev_empty_when_nothing_matches(dl):
    assert dl.kev_to_markdown([_kev("CVE-1", "Adobe", "Reader", "x")], ["nginx"]) == {}


SIGMA_RULE = """
title: SQL Injection Strings In URI
id: 5513deaf-f49a-46c2-a6c8-3f111b5cb453
status: test
description: Detects potential SQL injection attempts in web server access logs.
tags:
    - attack.initial-access
    - attack.t1190
logsource:
    category: webserver
detection:
    keywords:
        - "' OR 1=1"
        - "UNION SELECT"
    condition: keywords
falsepositives:
    - Internal vulnerability scanners
    - User searches in search boxes
level: high
"""


def test_sigma_rule_to_markdown_keeps_logic_and_false_positives(dl):
    md = dl.sigma_to_markdown(SIGMA_RULE, "https://example.test/rule.yml")
    assert md.startswith("## Sigma rule: SQL Injection Strings In URI")
    assert "Level: high." in md and "ATT&CK techniques: T1190." in md and "Tactics: initial-access." in md
    assert "```yaml" in md and "UNION SELECT" in md
    assert "Known false positives for 'SQL Injection Strings In URI': Internal vulnerability scanners; User searches in search boxes" in md


def test_sigma_rule_invalid_input_returns_empty(dl):
    assert dl.sigma_to_markdown("not: [valid", "u") == ""
    assert dl.sigma_to_markdown("just a string", "u") == ""
    assert dl.sigma_to_markdown("description: no title here\n", "u") == ""
