# Knowledge base (`data/knowledge_base/`)

Everything the AI investigator can look up. Each **top-level folder is a
category**; the investigator asks three separate questions per alert and
answers each from specific folders (see `docs/rag.md`).

```
mitre_attack/            enterprise_attack.json - raw MITRE ATT&CK STIX (downloaded)
nist/                    sp_800_61_rev3.pdf, csf_2.0.pdf, sp_800_92.pdf (downloaded PDFs)
owasp/                   logging_cheat_sheet.md, api_security_top10.md, top_10_2021/,
                         cheat_sheets/, wstg/ (downloaded)
attack_knowledge/        what each attack is and how it shows up in logs (hand-written)
investigation_playbooks/ how to verify each alert type (hand-written)
response_playbooks/      what to recommend for each alert type (hand-written)
vulnerability_knowledge/ weaknesses and fixes (hand-written) + cwe/ (downloaded)
windows/                 Windows Security logon event reference (hand-written)
detection_rules/         how IntelliSOC's own rules work (hand-written) + sigma/ (downloaded)
threat_intel/            cisa_kev/ exploited CVEs, nvd/ recent CVEs (downloaded)
hardening/               Mozilla OpenSSH guideline (downloaded)
custom/                  analyst uploads from the UI + TEMPLATE_* files
```

Downloaded folders are git-ignored and rebuilt with
`.\scripts\download_knowledge_base.ps1 -All`. Hand-written documents are
tracked in git.

## File types

| Type | How it is indexed |
|---|---|
| `.md` / `.txt` | split on headings; each chunk is labelled with its section, e.g. `[Brute Force Response > Containment]` |
| `.pdf` | one section per page, running headers/footers removed; chunks cite the page, e.g. `[NIST SP 800-61 Rev. 3 \| p. 14]`. Scanned PDFs need OCR first (no extractable text). |
| `.json` | MITRE ATT&CK STIX bundle only: one section per live technique, with tactics, platforms, detection notes and mitigations |

Published documents stay in their original format (PDFs as PDFs); our own
playbooks are markdown because headings give precise citations and they
are easy to edit and review.

A PDF (or JSON) has no frontmatter, so its display title comes from an
optional `_metadata.json` in the same folder:

```json
{"sp_800_61_rev3.pdf": {"title": "NIST SP 800-61 Rev. 3", "source": "https://..."}}
```
Without one, the PDF's embedded title or the file name is used.

## Current state of the hand-written folders

The folder layout is complete, but several hand-written documents do not
exist yet. The rule-to-document map in
`backend/app/services/rag/rule_knowledge.py` already names them; until they
are added, the investigator falls back to searching the whole playbook
folder, so investigations still get guidance.

| Folder | Present | Still to be written |
|---|---|---|
| `attack_knowledge/` | `ssh_bruteforce.md` | `credential_attacks.md`, `sql_injection.md`, `xss.md`, `path_traversal.md`, `command_injection.md` |
| `investigation_playbooks/` | `brute_force.md` | `successful_login_after_bruteforce.md`, `suspicious_login.md`, `excessive_auth_failures.md`, `web_attack.md` |
| `response_playbooks/` | `brute_force_response.md`, `web_attack_response.md`, `windows_brute_force_response.md` | `compromised_account.md`, `escalation.md` |
| `vulnerability_knowledge/` | (CWE catalogue, downloaded) | `sql_injection.md`, `xss.md`, `path_traversal.md`, `authentication.md` |

Use exactly these file names so the rule mapping picks them up.

## Adding your own documents

1. **From the UI** - *Knowledge Base -> Add document (.md / .txt / .pdf)*.
   Saved to `custom/` and indexed immediately; custom documents can be
   deleted from the same page.
2. **On disk** - put the file in the folder that matches its purpose
   (e.g. a response procedure in `response_playbooks/`) and run
   `.\scripts\ingest_knowledge_base.ps1`.

Markdown files should start with a frontmatter block:

```markdown
---
title: Lab SSH Runbook
source: FYP lab wiki
---
```

The `custom/TEMPLATE_*.md` files (asset context, escalation policy, approved
containment actions, known benign sources, past incidents) describe the
organisation-specific documents that help the AI most. Copy one to a name
without the `TEMPLATE_` prefix, fill it in, and ingest; `TEMPLATE_*`,
`README*` and `_*` files are never indexed.

## What not to add

- Whole-year CVE dumps or all of NVD: hundreds of thousands of chunks bury
  the playbooks. Keep CVE data keyword-scoped (the `nvd` source does).
- CIS Benchmarks: the licence forbids redistribution.
- Vendor marketing, long textbooks, or anything unrelated to the alerts
  IntelliSOC raises: it competes in search and displaces the playbooks.

## Maintenance

- `.\scripts\ingest_knowledge_base.ps1` is incremental: unchanged files are
  skipped (content hash), changed files have their old chunks replaced,
  and chunks of deleted files are removed.
- After changing the embedding model or `RAG_DOC_PREFIX`/`RAG_QUERY_PREFIX`,
  run it with `-Reset` - the index refuses to mix vectors from different
  embedding setups and says so.
- `backend/scripts/evaluate_rag.py` measures retrieval quality after
  changes (see `docs/rag.md`).
