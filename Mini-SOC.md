# MASTER ENGINEERING PROMPT
## Agentic AI-Based Mini-SOC

You are the lead software engineer responsible for building the complete project:

**“An Agentic AI-Based Mini-SOC for Automated Tier-1 Security Alert Triage, Investigation, Threat Intelligence Enrichment, and Response Recommendation using Local LLMs and RAG.”**

Build this as a complete, functional, student-friendly FYP system.

---

# 1. PRIMARY OBJECTIVE

Build a small automated Security Operations Center that assists a Tier-1 SOC analyst with:

1. Security log ingestion
2. Log parsing
3. Event normalization
4. Deterministic threat detection
5. Alert generation
6. Alert correlation
7. Incident creation
8. Threat intelligence enrichment
9. RAG-based security knowledge retrieval
10. Local LLM analysis using Ollama
11. Agentic investigation
12. Risk assessment
13. Response recommendation
14. OWASP-focused website security scanning
15. Investigation/report generation
16. SOC dashboard visualization

The system must automate repetitive Tier-1 investigation tasks while keeping the human analyst in control.

---

# 2. MOST IMPORTANT DEVELOPMENT RULE

DO NOT ask the user for permission after every phase.

Automatically progress through the development phases.

The development cycle must be:

```text
Implement
→ Test
→ Verify
→ Fix problems
→ Re-test
→ Continue to next phase
```

Only stop and ask the user if:

- a major architectural decision is required that is not defined in this prompt
- a required external credential/API key is genuinely necessary
- the existing project contains a serious conflict that cannot safely be resolved
- continuing would require changing the fundamental project scope

For normal bugs, missing imports, failed tests, dependency issues, API mismatches, parser problems, database errors, frontend errors, or integration problems:

**Fix them yourself and continue.**

Do not stop merely because something fails.

---

# 3. DEVELOPMENT MILESTONES

Build the entire system through these milestones.

## MILESTONE 1: CORE SOC

Implement:

- project foundation
- backend
- frontend
- database
- authentication
- log ingestion
- parsing
- normalization
- detection
- alerts
- correlation
- incidents

Mandatory milestone test:

```text
auth.log
→ parser
→ normalized events
→ detection
→ alert
→ correlation
→ incident
```

Do not continue until this works.

---

## MILESTONE 2: AI SOC ENGINE

Implement:

- RAG
- knowledge base
- vector database
- embeddings
- Ollama
- local LLM integration
- threat intelligence
- risk engine
- investigation agent
- investigation tools
- structured AI output

Mandatory test:

```text
Alert
→ Agent investigation
→ Related evidence
→ Threat intelligence
→ RAG
→ Ollama
→ Risk assessment
→ AI analysis
→ Response recommendation
```

---

## MILESTONE 3: COMPLETE SOC APPLICATION

Implement:

- SOC orchestrator
- website security scanner
- reports
- complete dashboard
- alert investigation UI
- incident UI
- investigation trace
- threat intelligence UI
- scan results
- report generation

Mandatory test:

```text
Log
→ Alert
→ Incident
→ AI Investigation
→ Report
→ Dashboard
```

---

## MILESTONE 4: FINALIZATION

Implement:

- complete integration testing
- security hardening
- error handling
- logging/observability
- Docker support
- documentation
- sample data
- demo scenarios
- final cleanup

Then run the complete golden-path test.

---

# 4. TECHNOLOGY STACK

Use this stack unless a genuine technical conflict requires an alternative.

## Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Uvicorn
- PostgreSQL

SQLite may be used temporarily during local development if necessary, but maintain PostgreSQL-compatible models and schema.

## Frontend

- React
- Vite
- TypeScript
- Tailwind CSS
- suitable chart library

## AI

- Ollama
- configurable local LLM
- local embedding model

## RAG

Prefer:

- chromadb

ChromaDB is acceptable .

Use LangChain or LlamaIndex only where they genuinely simplify implementation.

Do not introduce unnecessary frameworks.

## ML

- scikit-learn
- Isolation Forest

ML is supplementary and must never independently declare an attack.

## Deployment

- Docker
- docker-compose

The application must also be runnable locally without Docker.

---

# 5. PROJECT STRUCTURE

Use a clean modular architecture similar to:

```text
mini-soc/

├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   └── dependencies.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── database/
│   │   ├── services/
│   │   │   ├── ingestion/
│   │   │   ├── parsing/
│   │   │   ├── normalization/
│   │   │   ├── detection/
│   │   │   ├── correlation/
│   │   │   ├── investigation/
│   │   │   ├── threat_intel/
│   │   │   ├── rag/
│   │   │   ├── llm/
│   │   │   ├── risk/
│   │   │   └── reporting/
│   │   ├── agents/
│   │   ├── tools/
│   │   └── utils/
│   └── tests/

├── soc-agent/
│   ├── agent.py
│   ├── collector.py
│   ├── parser.py
│   ├── normalizer.py
│   ├── sender.py
│   └── config.yaml

├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── services/
│       ├── hooks/
│       ├── types/
│       └── utils/

├── rag/
├── data/
│   ├── sample_logs/
│   ├── knowledge_base/
│   └── threat_intel/

├── website-scanner/
├── scripts/
├── docs/
├── tests/

├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

Do not create directories that serve no purpose.

Keep the architecture simple enough for a university FYP.

---

# 6. CORE DATA FLOW

The primary architecture is:

```text
Security Logs
      ↓
Log Ingestion
      ↓
Parsing
      ↓
Normalization
      ↓
Detection Engine
      ↓
Alert
      ↓
Correlation
      ↓
Incident
      ↓
Agentic Investigation
      ↓
Evidence Collection
      ↓
Threat Intelligence
      ↓
RAG
      ↓
Local LLM
      ↓
Risk Assessment
      ↓
Response Recommendation
      ↓
Report
      ↓
SOC Dashboard
```

The AI must NOT simply receive raw logs and guess whether they are malicious.

Instead:

```text
Rules detect
Correlation connects
Threat Intelligence contextualizes
RAG provides knowledge
LLM analyzes evidence
Agent orchestrates investigation
Risk engine provides transparent scoring
Human analyst remains in control
```

---

# 7. LOG INPUTS

Support:

1. Linux auth.log
2. Linux syslog
3. Apache access logs
4. Apache error logs
5. Nginx access logs
6. Nginx error logs
7. CSV
8. JSON

Windows Event Logs may be implemented only if the core system is already stable.

Do not allow Windows support to delay the MVP.

---

# 8. LOG INGESTION

Implement:

```text
POST /api/logs/upload
POST /api/events
GET /api/logs
GET /api/logs/{id}
```

Uploaded logs must:

- be validated
- have file-size limits
- never execute
- be parsed safely
- generate structured events
- preserve raw log information
- record timestamps where possible
- identify source IP where possible
- identify username where possible
- identify event type
- identify host/source

---

# 9. NORMALIZED EVENT MODEL

Create a normalized event representation containing fields such as:

```text
id
timestamp
source
source_type
host
source_ip
destination_ip
username
event_type
action
status
message
raw_log
metadata
```

Different log formats must be converted into this common representation.

---

# 10. DETECTION ENGINE

Detection must be deterministic, modular, configurable, and evidence-producing.

Implement at minimum:

## Rule 1: SSH Brute Force

Default:

```text
10 or more failed authentication attempts
from the same IP
within 5 minutes
```

Generate:

```text
HIGH
```

alert.

Make the threshold configurable.

---

## Rule 2: Failed Logins Followed By Success

Detect:

```text
multiple failed login attempts
+
successful login
+
same source IP
```

Generate elevated:

```text
HIGH / CRITICAL
```

severity depending on evidence.

---

## Rule 3: SQL Injection

Detect common SQL injection patterns in web logs.

Examples include suspicious query parameters and SQL syntax patterns.

Generate evidence showing exactly what triggered the rule.

---

## Rule 4: XSS

Detect common reflected/stored XSS indicators in web access logs.

---

## Rule 5: Path Traversal

Detect:

```text
../
encoded traversal
```

and similar patterns.

---

## Rule 6: Sensitive File Access

Detect suspicious requests for files such as:

```text
/etc/passwd
/etc/shadow
```

---

## Rule 7: Excessive Authentication Failures

Detect abnormal authentication failure frequency.

---

# 11. DETECTION EVIDENCE

Every alert must contain evidence.

Example:

```json
{
  "rule": "SSH_BRUTE_FORCE",
  "source_ip": "192.168.1.50",
  "failed_attempts": 43,
  "time_window": "5 minutes",
  "evidence": [
    "43 failed SSH authentication attempts",
    "Same source IP observed repeatedly"
  ]
}
```

Never create an alert without explaining what evidence triggered it.

---

# 12. ALERT LIFECYCLE

Implement:

```text
NEW
↓
ACKNOWLEDGED
↓
INVESTIGATING
↓
RESOLVED
```

Optional:

```text
FALSE_POSITIVE
```

Alert fields should include:

- ID
- title
- severity
- confidence
- timestamp
- source IP
- username
- host
- detection rule
- evidence
- status
- incident ID

---

# 13. INCIDENT CORRELATION

Group related events using:

- time
- source IP
- username
- host
- attack pattern
- related alert types

Example:

```text
43 failed SSH attempts
+
successful login
+
post-login activity
```

should preferably become one investigation/incident rather than unrelated alerts.

---

# 14. DATABASE

Implement these core entities:

```text
User
Agent
LogEvent
Alert
Incident
Investigation
ThreatIntel
WebsiteScan
Report
```

Relationships:

```text
Agent
 ↓
LogEvents
 ↓
Alerts
 ↓
Incident
 ↓
Investigation
 ↓
Report
```

Use foreign keys and indexes for:

- timestamp
- source_ip
- event_type
- severity
- status
- incident_id

---

# 15. SOC ENDPOINT AGENT

Create a lightweight Python agent.

It should be capable of monitoring:

```text
/var/log/auth.log
/var/log/syslog
/var/log/apache2/access.log
```

where available.

The agent should:

```text
collect
→ parse
→ normalize
→ send events to backend
```

The agent must authenticate to the backend.

Never hard-code credentials.

For Windows development, provide sample/synthetic logs so the entire FYP can still be demonstrated.

---

# 16. RAG KNOWLEDGE BASE

Build a cybersecurity knowledge base containing:
download necessary stuff from web or ask the user to do so or let it space confine just so user could add later give user the choice cause based upon this knowledge base decsions would be made

- OWASP Top 10
- MITRE ATT&CK
- CWE
- CVE/NVD information
- NIST/security guidance
- incident response procedures
- Linux authentication security
- SSH brute force
- SQL injection
- XSS
- path traversal
- internal detection rules
- response playbooks

Pipeline:

```text
Document
→ Load
→ Clean
→ Chunk
→ Embed
→ Vector Database
```

Query:

```text
Agent question
→ Embedding
→ Similarity Search
→ Relevant chunks
→ Local LLM
```

Return source metadata whenever possible.

Never dump the entire knowledge base into the LLM.

---

# 17. OLLAMA

Integrate Ollama through a dedicated service.
also make a service which helps in using cloud ollama service an alt to local ollama 
Use environment variables:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=your_model
OLLAMA_TIMEOUT=120
OLLAMA_TEMPERATURE=0.1
```

The application must gracefully handle:

- Ollama unavailable
- model unavailable
- timeout
- connection error
- malformed JSON
- slow model response

The system must remain usable even when the local LLM is unavailable.

---

# 18. LOCAL LLM RESPONSIBILITY

The LLM is a Tier-1 SOC investigation assistant.

It must:

- analyze supplied evidence
- explain alerts
- summarize incidents
- assess possible impact
- use retrieved security knowledge
- use supplied threat intelligence
- suggest response actions
- provide confidence
- map findings to MITRE/OWASP where justified

It must NEVER:

- invent log events
- invent IP reputation
- invent CVEs
- invent timestamps
- invent threat intelligence
- claim an action was executed when it was only recommended
- assume compromise without evidence

If evidence is insufficient:

```text
Insufficient evidence to determine malicious activity with confidence.
```

---

# 19. STRUCTURED LLM OUTPUT

Prefer validated JSON such as:

```json
{
  "attack_type": "SSH Brute Force",
  "severity": "HIGH",
  "confidence": 0.91,
  "summary": "Multiple failed SSH authentication attempts were observed from the same source IP.",
  "evidence": [
    "43 failed attempts within 5 minutes",
    "Same source IP observed repeatedly"
  ],
  "threat_context": "...",
  "impact": "...",
  "mitre_technique": "T1110",
  "recommended_actions": [
    "Review successful login activity",
    "Investigate the source IP",
    "Review account activity",
    "Consider blocking the source IP"
  ],
  "requires_human_approval": true
}
```

Validate this using Pydantic.

---

# 20. EVIDENCE PROVENANCE

Clearly distinguish:

```text
EVIDENCE
What the system directly observed.

THREAT INTELLIGENCE
Information from TI providers.

KNOWLEDGE
Information retrieved from RAG.

INFERENCE
AI-generated conclusion based on the above.
```

The LLM must not mix these categories.

---

# 21. AGENTIC AI

Build ONE investigation orchestrator.

Do NOT create a complicated multi-agent swarm.

The agent should dynamically choose relevant tools.

Available tools should include:

```text
get_alert_details(alert_id)

search_related_logs(
    source_ip,
    username,
    start_time,
    end_time,
    event_type
)

get_related_events()

get_agent_info()

get_ip_threat_intelligence(ip)

get_domain_threat_intelligence(domain)

lookup_cve()

search_security_knowledge(query)

search_previous_incidents()

get_response_playbook()

calculate_risk(evidence)

generate_report(investigation)
```

The agent must NOT blindly call every tool.

---

# 22. AGENT WORKFLOW

Implement:

```text
1. Receive alert
2. Understand alert
3. Determine missing evidence
4. Search related logs
5. Extract indicators
6. Perform relevant threat intelligence enrichment
7. Retrieve relevant RAG knowledge
8. Check previous incidents where useful
9. Aggregate evidence
10. Calculate risk
11. Send structured evidence to local LLM
12. Validate LLM output
13. Generate response recommendation
14. Determine escalation requirement
15. Generate investigation result
16. Complete investigation
```

---

# 23. AGENT TRACE

Display an auditable investigation trace.

Example:

```text
[1] Alert received
[2] Alert identified as possible SSH brute force
[3] Related authentication events searched
[4] 43 failed attempts found
[5] Successful login detected
[6] Source IP extracted
[7] Threat intelligence lookup completed
[8] SSH security guidance retrieved from RAG
[9] Risk calculated
[10] Evidence sent to local LLM
[11] AI analysis validated
[12] Response recommendation generated
[13] Investigation completed
```

Do not expose hidden chain-of-thought.

Only expose concise tool/action summaries, observations, evidence, and decisions.

---

# 24. THREAT INTELLIGENCE
could use virus total api for threat intel too 
Create:

```text
ThreatIntelProvider
```

with:

```text
LocalThreatIntelProvider
```

as mandatory.

Optional providers:

```text
VirusTotal
NVD
```

Support:

- IP
- domain
- hash
- CVE

Local synthetic threat intelligence must exist so the system works offline.

Display:

- indicator
- reputation
- classification
- source
- confidence
- timestamp
- details

External TI failure must never crash an investigation.

---

# 25. RISK ENGINE

Create a transparent deterministic risk engine.

Consider:

- detection severity
- evidence quantity
- successful compromise indicators
- threat intelligence
- anomaly score
- asset context

Output:

```text
risk_score
severity
confidence
risk_factors
```

The LLM must not arbitrarily choose severity without evidence.

---

# 26. MACHINE LEARNING

Implement Isolation Forest as an optional supporting anomaly detector.

Possible features:

```text
failed_login_count
request_frequency
unique_usernames
unique_ips
requests_per_minute
HTTP_status_distribution
authentication_frequency
```

Output:

```text
anomaly_score
is_anomaly
```

Important:

**ML must NEVER independently declare that an attack occurred.**

It is supporting evidence only.

---

# 27. WEBSITE SECURITY SCANNER

Create a separate OWASP-focused scanner.

Input:

```text
target URL
```

Output:

```text
finding
severity
evidence
affected URL
OWASP category
description
recommendation
```

Focus on safe OWASP Top 10 checks.

Include SSRF protections.

Only support authorized lab targets.

Do not build a full penetration-testing framework.

Do not allow arbitrary payload execution.

Do not allow the scanner to delay the core SOC MVP.

---

# 28. RESPONSE RECOMMENDATIONS

The system provides recommendations.

It does NOT automatically execute destructive actions.

Examples:

### SSH brute force

Recommend:

- investigate source IP
- review successful logins
- review post-authentication activity
- consider credential reset
- enable/review MFA
- consider blocking IP
- investigate affected account
- escalate if compromise is suspected

### SQL Injection

Recommend:

- inspect endpoint
- inspect request parameters
- review database activity
- validate input handling
- patch vulnerable application
- escalate if exploitation is confirmed

### XSS

Recommend:

- inspect affected endpoint
- inspect input encoding
- review user/session impact
- patch application

### Path Traversal

Recommend:

- inspect requested path
- determine whether sensitive data was exposed
- review server activity
- patch application
- escalate if exposure is confirmed

Clearly distinguish:

```text
RECOMMENDED
```

from:

```text
EXECUTED
```

Initially, no destructive action should be executed.

---

# 29. HUMAN-IN-THE-LOOP

Potential future actions may include:

```text
Block IP
Disable account
Terminate process
Isolate host
Modify firewall
```

These require analyst approval.

The AI may recommend them but must not execute them automatically in the MVP.

---

# 30. API

Implement at minimum:

```text
POST /api/events

POST /api/logs/upload

GET /api/logs

GET /api/logs/{id}

GET /api/alerts

GET /api/alerts/{id}

POST /api/alerts/{id}/investigate

GET /api/investigations/{id}

GET /api/investigations/{id}/trace

GET /api/incidents

GET /api/incidents/{id}

POST /api/rag/search

GET /api/threat-intel/{indicator}

POST /api/reports/{incident_id}

GET /api/dashboard/statistics

GET /api/health
```

Keep API routes thin.

Business logic belongs in services.

---

# 31. FRONTEND

Create a professional dark SOC dashboard.

Pages:

```text
/login

/dashboard

/alerts

/alerts/:id

/incidents

/incidents/:id

/investigations/:id

/logs

/agents

/threat-intel

/website-scans

/reports

/settings
```

Dashboard should show:

- critical alerts
- high alerts
- medium alerts
- low alerts
- open incidents
- active agents
- recent investigations
- threat indicators
- recent website scans


Charts:

- alerts over time
- severity distribution
- top source IPs
- event types
- incident status

---

# 32. ALERT DETAILS PAGE

Display:

- alert ID
- title
- severity
- confidence
- timestamp
- affected host
- source IP
- username
- detection rule
- raw logs
- normalized events
- related events
- evidence
- threat intelligence
- RAG sources
- AI analysis
- MITRE/OWASP mapping
- risk score
- recommended response
- agent trace

Include:

```text
Investigate with AI
```

button.

---

# 33. REPORTING

Generate:

- PDF reports
- JSON reports

Report should contain:

```text
Incident summary
Alert information
Timeline
Evidence
Threat intelligence
RAG sources
AI analysis
Risk score
Recommended response
MITRE/OWASP mapping
Investigation trace
```

Never state that containment occurred unless the system actually executed containment.

---

# 34. SECURITY REQUIREMENTS

Implement:

- password hashing
- JWT authentication
- API authentication for agents
- input validation
- file type validation
- file size limits
- safe URL validation
- SSRF protection
- CORS configuration
- secure database queries
- environment-based secrets
- no secrets committed to Git
- no arbitrary command execution
- uploaded logs must never execute
- LLM must not directly execute shell commands
- no secrets in application logs

---

# 35. OBSERVABILITY

Log important system events:

```text
log ingestion
parsing
normalization
detection
alert creation
correlation
investigation start
tool calls
RAG retrieval
threat intelligence lookup
LLM request
LLM validation
investigation completion
errors
```

Never log:

- passwords
- API keys
- JWT secrets
- sensitive credentials

---

# 36. TESTING

Create automated tests.

## Parser tests

Test:

- valid logs
- malformed logs
- empty logs
- invalid timestamps
- missing IP
- missing username

## Detection tests

Test:

```text
5 failed SSH attempts
→ no brute-force alert

10 failed attempts
→ alert

failed attempts + success
→ elevated alert

normal login
→ no alert

SQL injection
→ detection

XSS
→ detection

path traversal
→ detection

sensitive file access
→ detection
```

## Correlation tests

Test:

```text
related events
→ one incident
```

and:

```text
unrelated events
→ separate incidents
```

## RAG tests

Test:

- document ingestion
- chunking
- embedding
- retrieval
- source metadata

## LLM tests

Test:

- valid JSON
- malformed JSON
- timeout
- Ollama unavailable
- model unavailable
- low-quality output

## Agent tests

Test:

- tool selection
- evidence gathering
- investigation completion
- insufficient evidence handling

## API tests

Test:

- authentication
- event ingestion
- log upload
- alert retrieval
- incident retrieval
- investigation
- reports

---

# 37. GOLDEN-PATH TEST

This is the most important integration test.

Create synthetic data demonstrating:

```text
Multiple failed SSH logins
+
successful login
```

Then verify:

```text
Synthetic auth.log
        ↓
Upload
        ↓
Parse
        ↓
Normalize
        ↓
Store
        ↓
Brute-force detection
        ↓
HIGH alert
        ↓
Correlation
        ↓
Incident
        ↓
Investigate with AI
        ↓
Agent
        ↓
Related log search
        ↓
Source IP extraction
        ↓
Threat Intelligence
        ↓
RAG
        ↓
Ollama
        ↓
Risk assessment
        ↓
AI explanation
        ↓
Response recommendation
        ↓
Investigation report
        ↓
Dashboard
```

This workflow must work end-to-end before declaring the project complete.

---

# 38. ERROR HANDLING

Every major service must fail gracefully.

Examples:

```text
Database unavailable
→ clear API error

Ollama unavailable
→ investigation can continue with non-LLM evidence

RAG unavailable
→ investigation reports unavailable knowledge retrieval

Threat intelligence unavailable
→ continue using local evidence

Malformed log
→ reject or skip safely

Invalid URL
→ reject safely

Invalid LLM JSON
→ validate, retry if appropriate, then return structured failure
```

Never allow one optional AI component to bring down the entire SOC.

---

# 39. ENVIRONMENT CONFIGURATION

Create:

```text
.env.example
```

Include configurable values such as:

```env
DATABASE_URL=
SECRET_KEY=

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=
OLLAMA_TIMEOUT=120
OLLAMA_TEMPERATURE=0.1

QDRANT_URL=

VIRUSTOTAL_API_KEY=
NVD_API_KEY=
```

Never hard-code credentials.

---

# 40. SAMPLE DATA

Create realistic synthetic sample data for:

- SSH brute force
- successful login after failures
- normal authentication
- SQL injection
- XSS
- path traversal
- sensitive file access
- normal Apache/Nginx traffic

The demo must work without requiring a real production environment.

---

# 41. DOCUMENTATION

Create/update:

```text
README.md file should be updated accordingly and maintained
docs/architecture.md
docs/setup.md
docs/api.md
docs/agent-workflow.md
docs/rag.md
docs/testing.md
```

README must explain:

- project purpose
- architecture
- features
- prerequisites
- installation
- configuration
- Ollama setup
- RAG setup
- database setup
- running backend
- running frontend
- running agent
- running tests
- running Docker
- demo workflow

---

# 42. DEVELOPMENT BEHAVIOR

Before modifying existing files:

1. Inspect the existing file.
2. Understand its current behavior.
3. Preserve working functionality.
4. Make the smallest clean change necessary.

Do not overwrite working code blindly.

Do not duplicate functionality.

Do not create unnecessary abstractions.

Prefer simple, readable Python and TypeScript suitable for a university student to understand and defend.

---

# 43. PHASE COMPLETION PROTOCOL

After each phase:

1. Implement the phase.
2. Run relevant tests.
3. Fix failures.
4. Run tests again.
5. Verify integration.
6. Update documentation if necessary.
7. Record:
   - what was implemented
   - files created
   - files modified
   - tests performed
   - test results
   - known limitations
8. Automatically continue to the next phase.

DO NOT ask:

> “Should I proceed?”

unless a genuine blocking architectural decision exists.

---

# 44. MAJOR FAILURE PROTOCOL

If something cannot be completed exactly as specified:

Do NOT fake it.

Instead:

1. Identify the limitation.
2. Implement the safest functional fallback.
3. Clearly document the limitation.
4. Continue development if possible.

Never claim:

```text
implemented
```

when the feature is only mocked or partially implemented.

---

# 45. SCOPE CONTROL

This is a student FYP.

Do NOT expand into:

- enterprise SIEM
- complete EDR
- malware sandbox
- full penetration testing
- packet inspection platform
- autonomous exploitation
- autonomous destructive response
- custom foundation-model training
- huge multi-agent architecture
- unnecessary microservices
- Kubernetes
- complex cloud infrastructure

Prioritize:

```text
functional
→ reliable
→ explainable
→ demonstrable
→ secure
→ maintainable
```

over unnecessary complexity.

---

# 46. FINAL DEFINITION OF DONE

The project is complete only when:

### Core SOC

- [ ] logs can be uploaded
- [ ] logs are parsed
- [ ] events are normalized
- [ ] detection rules work
- [ ] alerts are generated
- [ ] alerts are correlated
- [ ] incidents are created

### AI

- [ ] RAG works
- [ ] Ollama works
- [ ] structured LLM output works
- [ ] agentic investigation works
- [ ] threat intelligence works
- [ ] risk engine works
- [ ] response recommendations work

### Application

- [ ] dashboard works
- [ ] alert details work
- [ ] incident pages work
- [ ] investigation trace works
- [ ] threat intelligence page works
- [ ] website scanner works
- [ ] reports work

### Security

- [ ] authentication works
- [ ] secrets are protected
- [ ] input validation exists
- [ ] uploaded files are safe
- [ ] SSRF protections exist
- [ ] agents authenticate
- [ ] destructive actions are not automatic

### Testing

- [ ] unit tests pass
- [ ] API tests pass
- [ ] integration tests pass
- [ ] golden-path demo passes

### Deployment

- [ ] local setup works
- [ ] Docker setup works
- [ ] README is complete

---

# 47. FINAL PRIORITY ORDER

When making engineering decisions, follow this order:

```text
1. Correctness
2. Working golden path
3. Security
4. Reliability
5. Explainability
6. Testing
7. Maintainability
8. UI polish
9. Advanced features
```

IMPORTANT Do not sacrifice the working SOC pipeline for flashy AI features.

---

# 48. START NOW

Begin by inspecting the existing project/repository.

Determine:

- what already exists
- what is missing
- what can be reused
- what needs modification

Then start implementing the project.

Do NOT generate a theoretical plan only.

Actually build the system.

Progress automatically through all milestones.

After every milestone:

```text
Implement
→ Test
→ Fix
→ Verify
→ Continue
```

Do not wait for user confirmation between normal phases.
also specify what stuff is to be downloaded just so it could be downloaded in at first seprately
also use exsisting ollama models local or cloud models

also let me know which documemts and data is rerquired just so I could add on to it or download it 

also update the readme.md file alongside to keep track of changes 

At the end, provide a final summary containing:

```text
PROJECT STATUS

Completed:
...

Tests:
...

Golden-path result:
...

How to run:
...

Known limitations:
...

Important configuration:
...

Final project structure:
...
``

The ultimate objective is a **working, locally runnable, demonstrable Agentic AI Mini-SOC**, not merely a collection of code files.