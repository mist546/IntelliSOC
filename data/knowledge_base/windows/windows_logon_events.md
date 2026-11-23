---
title: Windows Security Logon Events Reference
category: reference
source: Internal reference, based on Microsoft Windows Security auditing documentation (event IDs 4624/4625/4740/4648/4672/1102)
---

# Windows Security Logon Events Reference

Windows does not write plain-text authentication logs. Logon activity is
recorded in the **Security** event log and this system ingests it from a
JSON export (`Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4624,4625,4740}
| Select-Object Id, TimeCreated, MachineName, Message | ConvertTo-Json`).
The parser maps event IDs to the same normalized event types as Linux
`auth.log`, so the brute-force rules apply to Windows logons unchanged.

## Event IDs and how this system normalizes them
- **4625 - An account failed to log on** -> `AUTH_FAILURE`. The core signal
  for brute force, password spraying and credential stuffing.
- **4624 - An account was successfully logged on** -> `AUTH_SUCCESS`. A 4624
  from the same source shortly after a burst of 4625s is the
  `FAILED_THEN_SUCCESS` pattern (possible successful brute force).
- **4740 - A user account was locked out** -> `ACCOUNT_LOCKOUT`. Confirms an
  account lockout policy fired; repeated 4740s across many accounts suggest
  password spraying rather than a single-account attack.
- **4648 - A logon was attempted using explicit credentials** ->
  `EXPLICIT_CREDENTIAL_LOGON` (RunAs / alternate credentials). Suspicious
  after a successful brute force because it can indicate lateral movement.
- **4672 - Special privileges assigned to new logon** ->
  `PRIVILEGE_ASSIGNED`. Immediately follows a 4624 for administrative
  accounts. A 4672 right after a brute-forced 4624 means the attacker
  obtained an administrative token.
- **4720 - A user account was created** -> `USER_CREATED`. A new account
  created after a suspicious logon is a persistence indicator.
- **1102 - The audit log was cleared** -> `AUDIT_LOG_CLEARED`. Almost always
  malicious outside planned maintenance (defense evasion, T1070.001).

## Fields inside the message and what they mean
- **Account Name** appears twice in 4624/4625: the first is the *Subject*
  (the process requesting the logon, often `-` or the machine account),
  the second is the *target* account being logged on. Investigations must
  use the second value. `-` as the subject is normal.
- **Source Network Address** is the remote IP for network logons. The
  values `-`, `::1` and `127.0.0.1` mean the logon was local (console,
  service, scheduled task), not remote - there is no attacker IP to
  investigate in that case.
- **Workstation Name** is self-reported by the client and can be spoofed
  (attack tools often send names like `KALI`, `WORKSTATION` or random
  strings); it is a weak indicator only.
- **Logon Process / Authentication Package**: `NtLmSsp` / `NTLM` on a
  4625 from an external IP is typical of SMB/RDP password guessing;
  `Kerberos` failures are usually domain-internal.

## Logon types (4624 / 4625 "Logon Type")
- **2 Interactive** - keyboard at the console.
- **3 Network** - SMB file share, WinRM, or a NTLM/RDP network logon. The
  logon type seen in almost all remote brute-force attempts.
- **4 Batch** - scheduled task.
- **5 Service** - a Windows service starting under an account.
- **7 Unlock** - workstation unlock.
- **8 NetworkCleartext** - credentials sent in clear text (e.g. basic
  authentication to IIS); always worth reviewing.
- **9 NewCredentials** - RunAs with `/netonly`.
- **10 RemoteInteractive** - Remote Desktop (RDP) / Terminal Services. A
  successful type-10 logon from an external IP after failures is a
  high-priority compromise indicator.
- **11 CachedInteractive** - logon with cached domain credentials while the
  domain controller is unreachable.

## 4625 failure status codes ("Status" / "Sub Status")
- **0xC000006D** - the logon failed (generic wrapper; look at Sub Status).
- **0xC000006A** - correct user name, wrong password. Many of these for one
  account from one IP = password guessing; one or two per account across
  many accounts = password spraying.
- **0xC0000064** - user name does not exist. Strong indicator of automated
  guessing with a wordlist (equivalent to Linux "invalid user").
- **0xC0000234** - account is locked out.
- **0xC0000072** - account is disabled. Repeated attempts against disabled
  accounts indicate the attacker is working from an old credential list.
- **0xC000006F** - logon outside permitted logon hours.
- **0xC0000070** - logon from an unauthorized workstation.
- **0xC0000071** - password expired.
- **0xC0000193** - account expired.
- **0xC000015B** - the user has not been granted the requested logon type
  on this machine (e.g. denied "log on through Remote Desktop").
- **0xC0000133** - clock skew too great (Kerberos).
- **0xC000018C** - trust relationship with the domain failed.

## Interpreting bursts
- Dozens of 4625 with Sub Status 0xC000006A against one account from one
  IP within minutes: **brute force / password guessing** (T1110.001).
- One or two 4625 per account against many accounts from one IP, often
  with the same password interval: **password spraying** (T1110.003) -
  designed to stay under lockout thresholds, so 4740 may never fire.
- 4625 with 0xC0000064 against names like `admin`, `test`, `backup`,
  `svc_*`: **wordlist-based guessing**, usually automated scanning.
- 4625 burst followed by 4624 (type 3 or 10) from the same IP, then 4672:
  **successful brute force with administrative access** - treat as a
  confirmed compromise candidate and investigate post-logon activity
  (4688 process creation, 4720 account creation, 7045 new service).

## Limits of the evidence
A Windows Security export only shows what the audit policy captured. If
"Audit Logon" failure auditing is disabled, 4625 events are absent and the
absence of failures is not evidence that no attack occurred. Timestamps in
exports are in the exporting machine's local time unless the export was
made in UTC.
