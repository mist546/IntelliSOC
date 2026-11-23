"""Download public security reference material into the RAG knowledge base.

Files land directly in the knowledge base layout (data/knowledge_base/):

    mitre_attack/enterprise_attack.json      raw MITRE ATT&CK STIX bundle (ingested as-is)
    nist/sp_800_61_rev3.pdf, csf_2.0.pdf, sp_800_92.pdf   original NIST PDFs (ingested per page)
    owasp/logging_cheat_sheet.md, api_security_top10.md, top_10_2021/, cheat_sheets/, wstg/
    vulnerability_knowledge/cwe/             CWE catalogue
    threat_intel/cisa_kev/, threat_intel/nvd/  exploited / recent CVEs
    detection_rules/sigma/                   community Sigma rules
    hardening/                               Mozilla OpenSSH guideline

The hand-written folders (attack_knowledge/, investigation_playbooks/,
response_playbooks/, vulnerability_knowledge/*.md, windows/) are bundled in
the repository and never touched by this script. Downloaded files are
git-ignored; re-run to refresh them. Then index everything:
    python scripts/ingest_knowledge_base.py

Usage:
    python scripts/download_knowledge_base.py --list
    python scripts/download_knowledge_base.py --all
    python scripts/download_knowledge_base.py --source nist --source mitre
    python scripts/download_knowledge_base.py --source nvd --nvd-keyword OpenSSH --nvd-keyword nginx

Sources (all opt-in):
    mitre        MITRE ATT&CK Enterprise STIX JSON               ~50 MB, one file
    nist         NIST SP 800-61r3, CSF 2.0, SP 800-92            3 PDFs (~6 MB)
    owasp        OWASP Logging Cheat Sheet, API Security Top 10 2023, 21 more cheat sheets (CC BY-SA 4.0)
    owasp-top10  OWASP Top 10 2021 chapters (official markdown; OWASP publishes no PDF for 2021)
    wstg         OWASP Web Security Testing Guide chapters         6 markdown files
    cwe          MITRE CWE weakness catalogue (view 1000)          ~0.6 MB zip -> ~10 md files
    kev          CISA Known Exploited Vulnerabilities (filtered)   ~1.5 MB JSON -> per-vendor md files
    nvd          Recent CVEs from the NVD API by keyword            small; NVD_API_KEY optional (faster)
    ssh          Mozilla OpenSSH hardening guideline (MPL 2.0)      1 markdown file
    sigma        Community Sigma detection rules (DRL 1.1)          ~8 YAML rules -> 1 md file
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import time
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402

settings = get_settings()
KB_ROOT = Path(settings.KNOWLEDGE_BASE_DIR)
TIMEOUT = httpx.Timeout(60.0, read=300.0)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _frontmatter(title: str, category: str, source: str) -> str:
    # Keep values on one line - the ingestion frontmatter parser is deliberately simple.
    def clean(value: str) -> str:
        return re.sub(r"\s+", " ", str(value)).replace(":", " -").strip()

    return f"---\ntitle: {clean(title)}\ncategory: {clean(category)}\nsource: {source}\n---\n\n"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    print(f"  wrote {path.relative_to(KB_ROOT).as_posix()} ({len(text) // 1024} KB)")


def _write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(f"  wrote {path.relative_to(KB_ROOT).as_posix()} ({len(data) // 1024} KB)")


def _write_titles(folder: Path, titles: dict[str, dict]) -> None:
    """_metadata.json gives PDFs/JSON (which have no frontmatter) a display
    title and source URL - read by app/services/rag/loaders.py."""
    meta_file = folder / "_metadata.json"
    existing = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}
    existing.update(titles)
    meta_file.write_text(json.dumps(existing, indent=2), encoding="utf-8")


def _get(client: httpx.Client, url: str, **kwargs) -> httpx.Response:
    resp = client.get(url, follow_redirects=True, **kwargs)
    resp.raise_for_status()
    return resp


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:60]


def _trim(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rsplit(" ", 1)[0] + "..."


# ---------------------------------------------------------------------------
# OWASP Cheat Sheet Series
# ---------------------------------------------------------------------------

OWASP_RAW = "https://raw.githubusercontent.com/OWASP/CheatSheetSeries/master/cheatsheets/"
OWASP_SHEETS = [
    "SQL_Injection_Prevention_Cheat_Sheet",
    "Cross_Site_Scripting_Prevention_Cheat_Sheet",
    "Injection_Prevention_Cheat_Sheet",
    "Input_Validation_Cheat_Sheet",
    "Authentication_Cheat_Sheet",
    "Credential_Stuffing_Prevention_Cheat_Sheet",
    "Session_Management_Cheat_Sheet",
    "Password_Storage_Cheat_Sheet",
    "File_Upload_Cheat_Sheet",
    "Server_Side_Request_Forgery_Prevention_Cheat_Sheet",
    "HTTP_Headers_Cheat_Sheet",
    "Vulnerable_Dependency_Management_Cheat_Sheet",
    # Ground the website scanner's header findings and the auth recommendations.
    "Content_Security_Policy_Cheat_Sheet",
    "Clickjacking_Defense_Cheat_Sheet",
    "HTTP_Strict_Transport_Security_Cheat_Sheet",
    "Transport_Layer_Security_Cheat_Sheet",
    "Multifactor_Authentication_Cheat_Sheet",
    "Forgot_Password_Cheat_Sheet",
    "Error_Handling_Cheat_Sheet",
    "REST_Security_Cheat_Sheet",
    "Secrets_Management_Cheat_Sheet",
]

OWASP_TOP10_RAW = "https://raw.githubusercontent.com/OWASP/Top10/master/2021/docs/en/"
OWASP_TOP10_CHAPTERS = [
    "A01_2021-Broken_Access_Control",
    "A02_2021-Cryptographic_Failures",
    "A03_2021-Injection",
    "A04_2021-Insecure_Design",
    "A05_2021-Security_Misconfiguration",
    "A06_2021-Vulnerable_and_Outdated_Components",
    "A07_2021-Identification_and_Authentication_Failures",
    "A08_2021-Software_and_Data_Integrity_Failures",
    "A09_2021-Security_Logging_and_Monitoring_Failures",
    "A10_2021-Server-Side_Request_Forgery_%28SSRF%29",
]

WSTG_RAW = "https://raw.githubusercontent.com/OWASP/wstg/master/document/4-Web_Application_Security_Testing/"
WSTG_CHAPTERS = [
    "07-Injection/05-SQL_Injection.md",
    "07-Injection/01-Reflected_Cross_Site_Scripting.md",
    "07-Injection/02-Stored_Cross_Site_Scripting.md",
    "07-Injection/11.1-File_Inclusion.md",
    "05-Authorization/01-Directory_Traversal_File_Include.md",
    "04-Authentication/03-Weak_Lock_Out_Mechanism.md",
]


API_TOP10_RAW = "https://raw.githubusercontent.com/OWASP/API-Security/master/editions/2023/en/"
API_TOP10_CHAPTERS = [
    "0xa1-broken-object-level-authorization",
    "0xa2-broken-authentication",
    "0xa3-broken-object-property-level-authorization",
    "0xa4-unrestricted-resource-consumption",
    "0xa5-broken-function-level-authorization",
    "0xa6-unrestricted-access-to-sensitive-business-flows",
    "0xa7-server-side-request-forgery",
    "0xa8-security-misconfiguration",
    "0xa9-improper-inventory-management",
    "0xaa-unsafe-consumption-of-apis",
]


def download_owasp(client: httpx.Client, args) -> None:
    owasp_dir = KB_ROOT / "owasp"
    url = f"{OWASP_RAW}Logging_Cheat_Sheet.md"
    _write(owasp_dir / "logging_cheat_sheet.md", _frontmatter("OWASP Logging Cheat Sheet", "owasp", url) + _get(client, url).text)

    chapters = []
    for name in API_TOP10_CHAPTERS:
        chapters.append(_get(client, f"{API_TOP10_RAW}{name}.md").text.strip())
    _write(
        owasp_dir / "api_security_top10.md",
        _frontmatter("OWASP API Security Top 10 2023", "owasp", API_TOP10_RAW) + "\n\n".join(chapters),
    )

    out_dir = owasp_dir / "cheat_sheets"
    for name in OWASP_SHEETS:
        url = f"{OWASP_RAW}{name}.md"
        body = _get(client, url).text
        title = name.replace("_", " ")
        _write(out_dir / f"{name.lower()}.md", _frontmatter(title, "owasp-cheatsheet", url) + body)


def download_owasp_top10(client: httpx.Client, args) -> None:
    out_dir = KB_ROOT / "owasp" / "top_10_2021"
    for name in OWASP_TOP10_CHAPTERS:
        url = f"{OWASP_TOP10_RAW}{name}.md"
        body = _get(client, url).text
        title = "OWASP Top 10 2021 - " + name.split("-", 1)[1].replace("_", " ").replace("%28", "(").replace("%29", ")")
        _write(out_dir / f"{_slug(name)}.md", _frontmatter(title, "owasp-top10", url) + body)


def download_wstg(client: httpx.Client, args) -> None:
    out_dir = KB_ROOT / "owasp" / "wstg"
    for rel in WSTG_CHAPTERS:
        url = f"{WSTG_RAW}{rel}"
        body = _get(client, url).text
        chapter = Path(rel).stem.split("-", 1)[-1].replace("_", " ")
        _write(out_dir / f"{_slug(chapter)}.md", _frontmatter(f"WSTG - Testing for {chapter}", "owasp-wstg", url) + body)


# ---------------------------------------------------------------------------
# MITRE ATT&CK Enterprise (STIX 2.1 JSON)
# ---------------------------------------------------------------------------

ATTACK_STIX_URL = (
    "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json"
)


def download_mitre(client: httpx.Client, args) -> None:
    """Saves the raw STIX bundle; ingestion turns every live technique and
    sub-technique (with its mitigations) into its own section."""
    print(f"  fetching {ATTACK_STIX_URL} (~50 MB)...")
    raw = _get(client, ATTACK_STIX_URL).content
    bundle = json.loads(raw)
    techniques = sum(
        1 for o in bundle.get("objects", [])
        if o.get("type") == "attack-pattern" and not o.get("revoked") and not o.get("x_mitre_deprecated")
    )
    out_dir = KB_ROOT / "mitre_attack"
    _write_bytes(out_dir / "enterprise_attack.json", raw)
    _write_titles(out_dir, {"enterprise_attack.json": {"title": "MITRE ATT&CK Enterprise", "source": ATTACK_STIX_URL}})
    print(f"  {techniques} live technique(s)/sub-technique(s)")


# ---------------------------------------------------------------------------
# MITRE CWE catalogue (Research Concepts view, CSV)
# ---------------------------------------------------------------------------

CWE_CSV_ZIP_URL = "https://cwe.mitre.org/data/csv/1000.csv.zip"


def download_cwe(client: httpx.Client, args) -> None:
    raw = _get(client, CWE_CSV_ZIP_URL).content
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        csv_name = next(n for n in z.namelist() if n.endswith(".csv"))
        rows = list(csv.DictReader(io.StringIO(z.read(csv_name).decode("utf-8", errors="replace"))))

    out_dir = KB_ROOT / "vulnerability_knowledge" / "cwe"
    batch_size = 100
    for start in range(0, len(rows), batch_size):
        batch = rows[start : start + batch_size]
        first, last = batch[0]["CWE-ID"], batch[-1]["CWE-ID"]
        parts = [_frontmatter(f"CWE catalogue CWE-{first} to CWE-{last}", "cwe", CWE_CSV_ZIP_URL)]
        for r in batch:
            parts.append(f"## CWE-{r['CWE-ID']}: {r['Name']}\n\n")
            parts.append(f"Abstraction: {r.get('Weakness Abstraction', '')}. Status: {r.get('Status', '')}.\n\n")
            parts.append(f"{_trim(r.get('Description', ''), 900)}\n\n")
            if r.get("Extended Description"):
                parts.append(f"{_trim(r['Extended Description'], 900)}\n\n")
            mitigations = r.get("Potential Mitigations", "")
            if mitigations:
                # The CSV encodes mitigations as ::PHASE:...:DESCRIPTION:...:: - keep the readable text.
                readable = re.sub(r"DESCRIPTION:", "- ", mitigations)
                readable = re.sub(r"::|PHASE:|STRATEGY:|EFFECTIVENESS:|NOTE:", " ", readable)
                parts.append(f"Potential mitigations for CWE-{r['CWE-ID']}: {_trim(readable, 700)}\n\n")
        _write(out_dir / f"cwe_{int(first):04d}_{int(last):04d}.md", "".join(parts))
    print(f"  {len(rows)} weakness(es)")


# ---------------------------------------------------------------------------
# CISA Known Exploited Vulnerabilities (KEV)
# ---------------------------------------------------------------------------

KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
# Only keep what this SOC's log sources can actually surface: web servers,
# Linux/SSH hosts, Windows hosts and the web-attack classes the rules detect.
DEFAULT_KEV_KEYWORDS = [
    "apache",
    "nginx",
    "openssh",
    "linux",
    "microsoft windows",
    "php",
    "wordpress",
    "sql injection",
    "cross-site scripting",
    "path traversal",
    "directory traversal",
    "authentication bypass",
]


KEV_MIN_PER_VENDOR_DOC = 5


def kev_to_markdown(vulnerabilities: list[dict], keywords: list[str]) -> dict[str, str]:
    """Filter KEV entries by keyword (matched against vendor, product and
    vulnerability name) and group them into one markdown document per
    vendor; vendors with fewer than KEV_MIN_PER_VENDOR_DOC matches share an
    "Other vendors" document. Returns {vendor_slug: markdown}."""
    lowered = [k.lower() for k in keywords]
    by_vendor: dict[str, list[dict]] = defaultdict(list)
    for v in vulnerabilities:
        blob = " ".join([v.get("vendorProject", ""), v.get("product", ""), v.get("vulnerabilityName", "")]).lower()
        if any(k in blob for k in lowered):
            by_vendor[v.get("vendorProject") or "Unknown"].append(v)

    grouped: dict[str, list[dict]] = defaultdict(list)
    for vendor, items in by_vendor.items():
        grouped[vendor if len(items) >= KEV_MIN_PER_VENDOR_DOC else "Other vendors"].extend(items)

    docs: dict[str, str] = {}
    for vendor, items in grouped.items():
        items.sort(key=lambda x: x.get("dateAdded", ""), reverse=True)
        parts = [_frontmatter(f"CISA KEV - actively exploited vulnerabilities - {vendor}", "cve-kev", KEV_URL)]
        parts.append(f"# CISA Known Exploited Vulnerabilities: {vendor}\n\n")
        for v in items:
            ransomware = v.get("knownRansomwareCampaignUse", "Unknown")
            parts.append(
                f"## {v.get('cveID')} - {v.get('vulnerabilityName', '')}\n\n"
                f"Product: {v.get('vendorProject', '')} {v.get('product', '')}. Added to KEV: {v.get('dateAdded', '')}. "
                f"Remediation due: {v.get('dueDate', '')}. Known ransomware campaign use: {ransomware}. "
                f"This CVE is confirmed exploited in the wild.\n\n"
                f"{_trim(v.get('shortDescription', ''), 700)}\n\n"
                f"Required action: {_trim(v.get('requiredAction', ''), 300)}\n\n"
            )
        docs[_slug(vendor)] = "".join(parts)
    return docs


def download_kev(client: httpx.Client, args) -> None:
    data = _get(client, KEV_URL).json()
    docs = kev_to_markdown(data.get("vulnerabilities", []), args.kev_keyword or DEFAULT_KEV_KEYWORDS)
    out_dir = KB_ROOT / "threat_intel" / "cisa_kev"
    for vendor_slug, markdown in sorted(docs.items()):
        _write(out_dir / f"kev_{vendor_slug}.md", markdown)
    total = sum(markdown.count("\n## ") for markdown in docs.values())
    print(f"  {total} exploited CVE(s) across {len(docs)} vendor(s) (catalog {data.get('catalogVersion', '?')})")


# ---------------------------------------------------------------------------
# NIST publications (original PDFs, ingested page by page)
# ---------------------------------------------------------------------------

NIST_DOCS = [
    (
        "NIST SP 800-61 Rev. 3 - Incident Response Recommendations and Considerations for Cybersecurity Risk Management",
        "https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-61r3.pdf",
        "sp_800_61_rev3.pdf",
    ),
    (
        "NIST Cybersecurity Framework (CSF) 2.0",
        "https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf",
        "csf_2.0.pdf",
    ),
    (
        "NIST SP 800-92 - Guide to Computer Security Log Management",
        "https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-92.pdf",
        "sp_800_92.pdf",
    ),
]


def download_nist(client: httpx.Client, args) -> None:
    out_dir = KB_ROOT / "nist"
    for title, url, filename in NIST_DOCS:
        _write_bytes(out_dir / filename, _get(client, url).content)
    _write_titles(out_dir, {filename: {"title": title, "source": url} for title, url, filename in NIST_DOCS})


# ---------------------------------------------------------------------------
# NVD CVE feed (recently modified CVEs for a keyword)
# ---------------------------------------------------------------------------

NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
DEFAULT_NVD_KEYWORDS = [
    "OpenSSH",
    "Apache HTTP Server",
    "nginx",
    "SQL injection",
    "cross-site scripting",
    "path traversal",
    "Windows SMB",
    "NTLM",
    "Remote Desktop",
    "PHP",
    "WordPress",
]


def download_nvd(client: httpx.Client, args) -> None:
    api_key = settings.NVD_API_KEY or os.environ.get("NVD_API_KEY", "")
    headers = {"apiKey": api_key} if api_key else {}
    # NVD allows 5 requests / 30 s without a key, 50 / 30 s with one.
    pause = 1.0 if api_key else 6.5
    keywords = args.nvd_keyword or DEFAULT_NVD_KEYWORDS

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=119)  # NVD caps date ranges at 120 days
    fmt = "%Y-%m-%dT%H:%M:%S.000"

    out_dir = KB_ROOT / "threat_intel" / "nvd"
    for keyword in keywords:
        params = {
            "keywordSearch": keyword,
            "lastModStartDate": start.strftime(fmt),
            "lastModEndDate": end.strftime(fmt),
            "resultsPerPage": args.nvd_limit,
        }
        try:
            data = _get(client, NVD_API_URL, params=params, headers=headers).json()
        except httpx.HTTPError as exc:
            print(f"  NVD request for '{keyword}' failed: {exc}")
            time.sleep(pause)
            continue

        entries = []
        for item in data.get("vulnerabilities", []):
            cve = item.get("cve", {})
            desc = next((d["value"] for d in cve.get("descriptions", []) if d.get("lang") == "en"), "")
            metrics = cve.get("metrics", {})
            score = severity = None
            for key in ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                if metrics.get(key):
                    cvss = metrics[key][0].get("cvssData", {})
                    score = cvss.get("baseScore")
                    severity = cvss.get("baseSeverity") or metrics[key][0].get("baseSeverity")
                    break
            refs = [r["url"] for r in cve.get("references", [])[:3]]
            entries.append(
                f"## {cve.get('id')}\n\n"
                f"Published: {cve.get('published', '')[:10]}. Last modified: {cve.get('lastModified', '')[:10]}. "
                f"CVSS base score: {score if score is not None else 'n/a'} ({severity or 'n/a'}). "
                f"Keyword: {keyword}.\n\n{_trim(desc, 1200)}\n\n"
                + (f"References: {', '.join(refs)}\n\n" if refs else "")
            )
        if entries:
            title = f"NVD CVEs matching '{keyword}' (modified {start:%Y-%m-%d} to {end:%Y-%m-%d})"
            _write(out_dir / f"cve_{_slug(keyword)}.md", _frontmatter(title, "cve-nvd", NVD_API_URL) + "".join(entries))
        print(f"  '{keyword}': {len(entries)} CVE(s) (total in NVD for range: {data.get('totalResults', '?')})")
        time.sleep(pause)


# ---------------------------------------------------------------------------
# SSH hardening (Mozilla OpenSSH guideline)
# ---------------------------------------------------------------------------

SSH_DOCS = [
    (
        "Mozilla OpenSSH security guidelines",
        "https://raw.githubusercontent.com/mozilla/infosec.mozilla.org/master/docs/guidelines/openssh.md",
        "mozilla_openssh_guidelines.md",
    ),
]


def download_ssh(client: httpx.Client, args) -> None:
    out_dir = KB_ROOT / "hardening"
    for title, url, filename in SSH_DOCS:
        body = _get(client, url).text
        # The Mozilla page has Jekyll frontmatter of its own - drop it so ours is the only one.
        if body.startswith("---"):
            body = body.split("---", 2)[-1].lstrip()
        _write(out_dir / filename, _frontmatter(title, "hardening", url) + body)


# ---------------------------------------------------------------------------
# Sigma detection rules (community, Detection Rule License 1.1)
# ---------------------------------------------------------------------------

SIGMA_RAW = "https://raw.githubusercontent.com/SigmaHQ/sigma/master/"
SIGMA_RULES = [
    "rules/linux/builtin/sshd/lnx_sshd_susp_ssh.yml",
    "rules/web/webserver_generic/web_sql_injection_in_access_logs.yml",
    "rules/web/webserver_generic/web_xss_in_access_logs.yml",
    "rules/web/webserver_generic/web_path_traversal_exploitation_attempt.yml",
    "rules/web/webserver_generic/web_source_code_enumeration.yml",
    "rules/web/webserver_generic/web_susp_useragents.yml",
    "rules/windows/builtin/security/win_security_susp_failed_logon_reasons.yml",
    "rules/windows/builtin/security/win_security_susp_logon_explicit_credentials.yml",
]


def sigma_to_markdown(rule_text: str, url: str) -> str:
    """Render one Sigma YAML rule as a markdown section: what it detects, its
    detection logic (as-is), the false positives the community documented,
    the level and the ATT&CK tags. Returns '' for unparsable input."""
    try:
        rule = yaml.safe_load(rule_text)
    except yaml.YAMLError:
        return ""
    if not isinstance(rule, dict) or not rule.get("title"):
        return ""
    tags = [t for t in rule.get("tags", []) if isinstance(t, str)]
    attack_ids = [t.split(".", 1)[1].upper() for t in tags if t.startswith("attack.t")]
    tactics = [t.split(".", 1)[1] for t in tags if t.startswith("attack.") and not t.startswith("attack.t")]
    falsepositives = [str(f) for f in rule.get("falsepositives", []) or []]
    logsource = rule.get("logsource", {}) or {}
    detection = yaml.safe_dump(rule.get("detection", {}), sort_keys=False, default_flow_style=False).strip()
    parts = [
        f"## Sigma rule: {rule['title']}\n\n",
        f"Level: {rule.get('level', 'unknown')}. Status: {rule.get('status', 'unknown')}. "
        f"Log source: {' / '.join(str(v) for v in logsource.values())}. "
        + (f"ATT&CK techniques: {', '.join(attack_ids)}. " if attack_ids else "")
        + (f"Tactics: {', '.join(tactics)}. " if tactics else "")
        + f"Source: {url}\n\n",
        f"{rule.get('description', '').strip()}\n\n",
        f"Detection logic:\n\n```yaml\n{detection}\n```\n\n",
    ]
    if falsepositives:
        parts.append(f"Known false positives for '{rule['title']}': {'; '.join(falsepositives)}\n\n")
    return "".join(parts)


def download_sigma(client: httpx.Client, args) -> None:
    sections = []
    for rel in SIGMA_RULES:
        url = f"{SIGMA_RAW}{rel}"
        try:
            section = sigma_to_markdown(_get(client, url).text, url)
        except httpx.HTTPError as exc:
            print(f"  skipped {rel}: {exc}")
            continue
        if section:
            sections.append(section)
    body = _frontmatter("Sigma community detection rules relevant to this SOC", "detection-rules", SIGMA_RAW)
    body += "# Sigma detection rules (SSH, web attacks, Windows logons)\n\n" + "".join(sections)
    _write(KB_ROOT / "detection_rules" / "sigma" / "sigma_rules.md", body)
    print(f"  {len(sections)} rule(s)")


# ---------------------------------------------------------------------------

SOURCES = {
    "owasp": ("OWASP Logging Cheat Sheet, API Security Top 10 2023 + 21 cheat sheets (CC BY-SA 4.0)", download_owasp),
    "owasp-top10": ("OWASP Top 10 2021 full chapters (CC BY-SA 4.0)", download_owasp_top10),
    "wstg": ("OWASP Web Security Testing Guide chapters for SQLi/XSS/traversal/LFI/lockout", download_wstg),
    "mitre": ("MITRE ATT&CK Enterprise (raw STIX JSON, ~50 MB)", download_mitre),
    "cwe": ("MITRE CWE weakness catalogue (view 1000, CSV -> markdown)", download_cwe),
    "kev": ("CISA Known Exploited Vulnerabilities, filtered to web/Linux/Windows/PHP (public domain)", download_kev),
    "nist": ("NIST SP 800-61r3, CSF 2.0 and SP 800-92 (original PDFs)", download_nist),
    "nvd": ("Recent CVEs from the NVD API by keyword (optional NVD_API_KEY)", download_nvd),
    "ssh": ("Mozilla OpenSSH hardening guideline (MPL 2.0)", download_ssh),
    "sigma": ("Community Sigma detection rules with documented false positives (DRL 1.1)", download_sigma),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="List available sources and exit.")
    parser.add_argument("--all", action="store_true", help="Download every source.")
    parser.add_argument("--source", action="append", choices=sorted(SOURCES), help="Source to download (repeatable).")
    parser.add_argument("--nvd-keyword", action="append", help="NVD: keyword to search (repeatable).")
    parser.add_argument("--kev-keyword", action="append", help="KEV: vendor/product/name keyword to keep (repeatable).")
    parser.add_argument("--nvd-limit", type=int, default=40, help="NVD: max CVEs per keyword (default 40).")
    args = parser.parse_args()

    if args.list or not (args.all or args.source):
        print("Available knowledge base sources:\n")
        for key, (desc, _) in SOURCES.items():
            print(f"  {key:12s} {desc}")
        print(f"\nKnowledge base directory: {KB_ROOT}")
        print("Example: python scripts/download_knowledge_base.py --source owasp --source mitre")
        return

    selected = sorted(SOURCES) if args.all else list(dict.fromkeys(args.source))
    failures = []
    with httpx.Client(timeout=TIMEOUT, headers={"User-Agent": "IntelliSOC-knowledge-base-downloader"}) as client:
        for key in selected:
            desc, fn = SOURCES[key]
            print(f"\n[{key}] {desc}")
            try:
                fn(client, args)
            except Exception as exc:  # noqa: BLE001 - one failing source must not abort the rest
                print(f"  FAILED: {exc}")
                failures.append(key)

    print("\nDone. Next step: python scripts/ingest_knowledge_base.py")
    if failures:
        print(f"Failed sources: {', '.join(failures)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
