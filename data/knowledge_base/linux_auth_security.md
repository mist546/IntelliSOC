---
title: Linux Authentication Security Basics
category: reference
source: Internal reference, informed by common Linux hardening guidance
---

# Linux Authentication Security Basics

## How SSH authentication events appear in auth.log
- `Failed password for <user> from <ip> port <port> ssh2` - a failed
  password authentication attempt for an existing account.
- `Failed password for invalid user <user> from <ip> port <port> ssh2` - the
  attempted username does not exist on the system at all, a strong
  indicator of automated scanning rather than a legitimate user mistake.
- `Accepted password for <user> from <ip> port <port> ssh2` - a successful
  password authentication.
- `session opened for user <user> by (uid=0)` - a PAM session was
  established following successful authentication.
- `sudo: <user> : ... COMMAND=<cmd>` - a privileged command execution via
  sudo, worth reviewing after any suspicious login.

## Why volume and timing matter
A handful of failed logins over a long period is normal (users mistype
passwords). A high volume of failed attempts in a short window, especially
against multiple usernames or from a single external IP, indicates
automated brute-force or credential-stuffing tooling rather than human
error. This is why detection thresholds are expressed as "N attempts within
a time window" rather than a raw total.

## Hardening recommendations
- Disable password authentication in favor of SSH key-based authentication
  where possible.
- Use `fail2ban` or equivalent to automatically and temporarily block
  source IPs after repeated failures.
- Disable root login over SSH (`PermitRootLogin no`).
- Enforce account lockout or rate limiting after repeated failures
  (CWE-307).
- Enable and monitor multi-factor authentication for privileged accounts.
- Regularly review `sudo` logs for unexpected privileged command usage.
