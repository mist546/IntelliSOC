---
title: SSH Brute Force Attacks
source: IntelliSOC attack knowledge (based on MITRE ATT&CK T1110 / T1021.004 and OpenSSH logging behaviour)
applies_to: SSH_BRUTE_FORCE, FAILED_THEN_SUCCESS, EXCESSIVE_AUTH_FAILURES
identifiers: T1110, T1110.001, T1021.004, T1098.004, T1053.003, CWE-307
---

# SSH Brute Force Attacks

## What it is
An SSH brute force attack is an automated attempt to log in to an SSH
server by trying many passwords (and often many usernames) until one
works. It maps to MITRE ATT&CK **T1110.001 Password Guessing** under
**T1110 Brute Force**; a successful login is then used for **T1021.004
Remote Services: SSH**. Any server with port 22 reachable from the
internet receives this traffic continuously - most of it comes from
botnets and scanning infrastructure, not from an attacker who has chosen
the organisation specifically.

## How attackers do it
- Tools such as Hydra, Medusa, Ncrack, Patator, or botnet malware (for
  example Mirai variants and cryptomining botnets) cycle through wordlists.
- Common target usernames: `root`, `admin`, `ubuntu`, `test`, `user`,
  `oracle`, `postgres`, `git`, `deploy`, `pi`, service names of installed
  software, and names taken from the organisation's website or email.
- Common passwords: default credentials, `123456`, `password`, seasonal
  passwords (`Summer2025!`) and passwords from public breach lists.
- Attempts are often spread over many source IPs (a botnet) and paced to
  stay below lockout thresholds.

## What it looks like in auth.log
- `Failed password for root from 203.0.113.55 port 51202 ssh2` - wrong
  password for an account that exists.
- `Failed password for invalid user admin from 203.0.113.55 port 51201 ssh2`
  and `Invalid user admin from 203.0.113.55 port 51201` - the username does
  not exist; a strong sign of automated guessing rather than a user typo.
- `Connection closed by authenticating user root 203.0.113.55 port 51230 [preauth]`
  and `Disconnected from invalid user ...` - the client gave up before
  authenticating, typical of fast scanners.
- `error: maximum authentication attempts exceeded for root from ...` - one
  connection tried more passwords than `MaxAuthTries` allows.
- `Accepted password for deploy from 203.0.113.55 port 51299 ssh2` after a
  burst of failures from the same IP - the attack may have succeeded.

## What distinguishes an attack from a user mistake
| Signal | Human mistake | Brute force |
|---|---|---|
| Failures per minute | 1-3 | tens to thousands |
| Usernames tried | the user's own | many, often non-existent |
| Source | known office/VPN address | unknown, hosting provider or residential botnet IP |
| Timing | business hours, irregular | constant rate, any hour |

## What attackers do after a successful SSH login
- Run reconnaissance: `uname -a`, `id`, `cat /proc/cpuinfo`, `w`.
- Add their own public key to `~/.ssh/authorized_keys` for persistence
  (T1098.004 SSH Authorized Keys).
- Create cron jobs or systemd services (T1053.003 Cron) that restart
  malware.
- Download and run cryptominers or botnet agents with `curl`/`wget`.
- Change the account's password to lock out competitors or the owner.
- Use the server to attack other internal machines (lateral movement).

## Why it matters for a small business
A single weak password on an internet-facing server is enough. Compromised
servers are commonly used for cryptomining (higher cloud bills, slow
services), spam or further attacks that get the business's IP blocklisted,
and as a foothold to reach internal systems and data.
