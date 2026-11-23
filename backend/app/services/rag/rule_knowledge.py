"""Which knowledge base documents belong to which detection rule.

The investigator asks three separate questions for every alert, each
answered from a different part of the knowledge base:
  investigation playbook  - how to check whether this alert is real
  response playbook       - what to recommend doing about it
  background knowledge    - what the attack is (attack/vulnerability
                            knowledge, MITRE ATT&CK, OWASP, NIST ...)
The mapping is deterministic so the right playbook is always consulted;
semantic search then picks the most relevant sections inside them. A
mapped document that does not exist (yet) is simply not found; if none of
a rule's documents exist, the tools fall back to searching the whole
folder (see app/tools/knowledge_tools.py).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class RuleKnowledge:
    topic: str  # plain-language description used to build search queries
    investigation: tuple[str, ...]
    response: tuple[str, ...]
    background: tuple[str, ...]
    identifiers: tuple[str, ...]  # ATT&CK / CWE / OWASP IDs, matched exactly


_AUTH_BACKGROUND_CATEGORIES = (
    "attack_knowledge", "vulnerability_knowledge", "mitre_attack", "windows", "hardening", "nist", "owasp",
)
_WEB_BACKGROUND_CATEGORIES = ("attack_knowledge", "vulnerability_knowledge", "mitre_attack", "owasp", "nist")

RULE_KNOWLEDGE: dict[str, RuleKnowledge] = {
    "SSH_BRUTE_FORCE": RuleKnowledge(
        topic="password brute force attack: many failed logins from one source IP in a short time",
        investigation=("investigation_playbooks/brute_force.md",),
        response=(
            "response_playbooks/brute_force_response.md",
            "response_playbooks/windows_brute_force_response.md",
            "response_playbooks/escalation.md",
        ),
        background=("attack_knowledge/ssh_bruteforce.md", "attack_knowledge/credential_attacks.md"),
        identifiers=("T1110.001", "T1110"),
    ),
    "FAILED_THEN_SUCCESS": RuleKnowledge(
        topic="successful login after repeated failed attempts from the same source: possible compromised account",
        investigation=(
            "investigation_playbooks/successful_login_after_bruteforce.md",
            "investigation_playbooks/suspicious_login.md",
        ),
        response=(
            "response_playbooks/compromised_account.md",
            "response_playbooks/brute_force_response.md",
            "response_playbooks/windows_brute_force_response.md",
            "response_playbooks/escalation.md",
        ),
        background=("attack_knowledge/credential_attacks.md", "vulnerability_knowledge/authentication.md"),
        identifiers=("T1078", "T1110"),
    ),
    "EXCESSIVE_AUTH_FAILURES": RuleKnowledge(
        topic="excessive authentication failures across accounts: password spraying or credential stuffing",
        investigation=("investigation_playbooks/excessive_auth_failures.md",),
        response=(
            "response_playbooks/brute_force_response.md",
            "response_playbooks/windows_brute_force_response.md",
            "response_playbooks/escalation.md",
        ),
        background=("attack_knowledge/credential_attacks.md", "vulnerability_knowledge/authentication.md"),
        identifiers=("T1110.003", "T1110.004"),
    ),
    "SQL_INJECTION": RuleKnowledge(
        topic="SQL injection attempt against a web application",
        investigation=("investigation_playbooks/web_attack.md",),
        response=("response_playbooks/web_attack_response.md", "response_playbooks/escalation.md"),
        background=("attack_knowledge/sql_injection.md", "vulnerability_knowledge/sql_injection.md"),
        identifiers=("CWE-89", "T1190", "A03:2021"),
    ),
    "XSS": RuleKnowledge(
        topic="cross-site scripting (XSS) attempt against a web application",
        investigation=("investigation_playbooks/web_attack.md",),
        response=("response_playbooks/web_attack_response.md", "response_playbooks/escalation.md"),
        background=("attack_knowledge/xss.md", "vulnerability_knowledge/xss.md"),
        identifiers=("CWE-79", "A03:2021"),
    ),
    "PATH_TRAVERSAL": RuleKnowledge(
        topic="path traversal (directory traversal) attempt to read files outside the web root",
        investigation=("investigation_playbooks/web_attack.md",),
        response=("response_playbooks/web_attack_response.md", "response_playbooks/escalation.md"),
        background=("attack_knowledge/path_traversal.md", "vulnerability_knowledge/path_traversal.md"),
        identifiers=("CWE-22", "T1083", "A01:2021"),
    ),
    "SENSITIVE_FILE_ACCESS": RuleKnowledge(
        topic="request for sensitive files on a web server such as .env, .git, backups or configuration files",
        investigation=("investigation_playbooks/web_attack.md",),
        response=("response_playbooks/web_attack_response.md", "response_playbooks/escalation.md"),
        background=("attack_knowledge/path_traversal.md", "vulnerability_knowledge/path_traversal.md"),
        identifiers=("CWE-538", "T1083", "A05:2021"),
    ),
}

DEFAULT_KNOWLEDGE = RuleKnowledge(
    topic="suspicious security event",
    investigation=("investigation_playbooks/suspicious_login.md",),
    response=("response_playbooks/escalation.md",),
    background=(),
    identifiers=(),
)


def knowledge_for(detection_rule: str | None) -> RuleKnowledge:
    return RULE_KNOWLEDGE.get(detection_rule or "", DEFAULT_KNOWLEDGE)


def background_categories(detection_rule: str | None) -> tuple[str, ...]:
    web_rules = {"SQL_INJECTION", "XSS", "PATH_TRAVERSAL", "SENSITIVE_FILE_ACCESS"}
    return _WEB_BACKGROUND_CATEGORIES if detection_rule in web_rules else _AUTH_BACKGROUND_CATEGORIES
