# IntelliSOC attack lab

A real, deliberately weak target you can attack from a real attacker box,
while IntelliSOC watches and raises alerts. No Wazuh needed - though there
is an optional Wazuh mode (see the end of this page).

```
 attacker (Kali, 172.28.0.66)  --attacks-->  target (172.28.0.10)
   hydra / curl / sqlmap / nikto             real sshd :22 + nginx :80
                                                   |
                                        writes auth.log + nginx_access.log to
                                        data/live_logs/lab/  (a bind mount)
                                                   |
                                        soc-agent tails them --> IntelliSOC
```

**Safety.** The target's ports are published only to `127.0.0.1`
(`2222`, `8080`), so the weak box is never exposed to your LAN. Attacks run
inside the Docker network. Only attack this lab.

## Prerequisites

Docker Desktop running, plus IntelliSOC itself up with the soc-agent
tailing (the agent's `config.yaml` already points at
`data/live_logs/lab/`). See `docs/setup.md` sections 1-4.

## Run it

```powershell
# 1. Start the lab (first build pulls Ubuntu + Kali, a few minutes)
cd lab
.\start_lab.ps1

# 2. Make sure the soc-agent is running (project root, its own terminal):
#    cd soc-agent; $env:MINISOC_AGENT_ID=...; $env:MINISOC_AGENT_KEY=...
#    .\.venv\Scripts\python.exe agent.py

# 3. Attack
.\attack.ps1 ssh-brute   # -> SSH_BRUTE_FORCE (HIGH), FAILED_THEN_SUCCESS (CRITICAL)
.\attack.ps1 web         # -> SQL_INJECTION, XSS, PATH_TRAVERSAL, SENSITIVE_FILE_ACCESS
.\attack.ps1             # interactive shell; cheatsheet prints on login
```

Watch the IntelliSOC dashboard: alerts appear within a couple of seconds of
each attack, correlate into incidents, and can be investigated with the AI
agent.

## What each attack triggers

| Command (on the attacker box)                                   | Alert |
|---|---|
| `hydra -l admin -P wordlists/passwords.txt ssh://target`        | `SSH_BRUTE_FORCE`, then `FAILED_THEN_SUCCESS` (admin's password `password123` is in the list) |
| `hydra -L wordlists/users.txt -P wordlists/passwords.txt ssh://target` | `SSH_BRUTE_FORCE`, `EXCESSIVE_AUTH_FAILURES` |
| `curl "http://target/search?q=' OR 1=1--"`                      | `SQL_INJECTION` |
| `curl "http://target/search?q=<script>alert(1)</script>"`       | `XSS` |
| `curl --path-as-is "http://target/../../etc/passwd"`            | `PATH_TRAVERSAL` |
| `curl "http://target/.env"`                                     | `SENSITIVE_FILE_ACCESS` |
| `sqlmap -u "http://target/search?q=test" --batch`               | `SQL_INJECTION` (many) |
| `nikto -h http://target`                                        | mix of the web rules |

## Notes

- **Dedup.** Alerts for the same IP + rule are suppressed for 30 min. To
  re-demo the same attack, mark the earlier alert RESOLVED or
  FALSE_POSITIVE first, or (SSH) brute force a different user.
- **Reset the target's logs:** `docker compose restart target` and delete
  `data/live_logs/lab/*.log` while the agent is stopped.
- **Stop / tear down:** `docker compose down --remove-orphans` (direct
  mode), or `docker compose -f docker-compose.yml -f docker-compose.wazuh.yml
  down -v` (Wazuh mode; `-v` also drops the target's log volume). The
  attacker's first build is large (Kali); it is cached afterwards.

## Wazuh mode

```powershell
.\start_lab.ps1 -Wazuh
```

Adds a Wazuh manager container and starts the Wazuh agent that is
installed in the target, so the logs take the route a real Wazuh shop
would use:

```
target sshd/nginx --> wazuh-agent --1514--> wazuh-manager (172.28.0.20)
   --> archives.json --> data/live_logs/wazuh/ (bind mount)
   --> soc-agent (already in config.yaml) --> IntelliSOC
```

- The attacks and the alerts they raise are the same as in the table above,
  with the host shown as `lab-web01` (the Wazuh agent's name) and Wazuh's
  rule ID, level and MITRE IDs kept in each event's metadata.
- In this mode the target's raw logs stay inside Docker, so nothing is
  reported twice; `.\start_lab.ps1` (no switch) goes back to direct mode.
- The manager takes about a minute to start. Check the agent with
  `docker compose -f docker-compose.yml -f docker-compose.wazuh.yml exec wazuh-manager /var/ossec/bin/agent_control -l`
  (`lab-web01 ... Active`).
- Files: `docker-compose.wazuh.yml`, `wazuh/` (manager image and
  `ossec.conf`), `target/wazuh-agent.conf`. Details and design notes:
  `docs/setup.md`, "Wazuh in Docker".
