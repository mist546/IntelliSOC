#!/usr/bin/env python
"""Attack simulator for live IntelliSOC demos.

Instead of uploading a static sample file, this plays an attack out in real
time so the dashboard can be watched reacting to it as it happens.

Scenarios
---------
ssh-brute-force (default)
    Appends sshd log lines, stamped with the current time, to the file the
    endpoint agent tails (data/live_logs/auth.log): a series of failed
    password attempts from one attacker IP, a few seconds apart, then
    (unless --no-success) a successful login. The agent forwards each line
    within ~2 s, so SSH_BRUTE_FORCE and then FAILED_THEN_SUCCESS fire live.
    The lines are simulated; nothing touches a real SSH server.

windows-logon  (Windows only)
    Makes REAL failed logon attempts against this machine through the
    Windows LogonUser API, so Windows itself writes genuine 4625 events to
    the Security log. Run the agent from an elevated terminal (so it can
    read that log) and the "Windows logon Brute Force" alert fires from the
    real event log. The default account name does not exist, so no real
    account is locked out. Needs "Audit Logon: Failure" enabled (the
    Windows default); check with: auditpol /get /subcategory:"Logon"

Usage (from the soc-agent folder, while the agent is running):
    python simulate_attack.py
    python simulate_attack.py --attempts 15 --delay 0.5 --ip random
    python simulate_attack.py --scenario windows-logon
"""
import argparse
import os
import random
import socket
import sys
import time
from datetime import datetime

DEFAULT_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "live_logs", "auth.log")
# 203.0.113.55 is listed as malicious in data/threat_intel/known_ips.json,
# so investigations of the default run show threat-intel enrichment.
DEFAULT_IP = "203.0.113.55"
TARGET_USERS = ["root", "admin", "ubuntu", "oracle", "postgres", "test", "deploy", "git"]
COMPROMISED_USER = "deploy"
SIM_WINDOWS_USER = "intellisoc-sim-user"


def syslog_time(now: datetime) -> str:
    # Classic syslog format: "Sep  5 14:03:07" (local time, space-padded day).
    return f"{now:%b} {now.day:2d} {now:%H:%M:%S}"


def pick_ip(value: str) -> str:
    if value != "random":
        return value
    # Documentation ranges (RFC 5737) - never a real host.
    return f"{random.choice(['198.51.100', '203.0.113'])}.{random.randint(2, 254)}"


def write_line(path: str, host: str, message: str) -> None:
    pid = random.randint(1000, 65000)
    line = f"{syslog_time(datetime.now())} {host} sshd[{pid}]: {message}"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def ssh_brute_force(args) -> None:
    path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    ip = pick_ip(args.ip)
    host = args.host

    print(f"[simulator] SSH brute force from {ip} against {host}: {args.attempts} attempts, ~{args.delay}s apart")
    print(f"[simulator] Writing to {path}\n")
    for _ in range(args.attempts):
        user = random.choice(TARGET_USERS)
        port = random.randint(40000, 65000)
        prefix = "" if user in ("root", COMPROMISED_USER) else "invalid user "
        write_line(path, host, f"Failed password for {prefix}{user} from {ip} port {port} ssh2")
        time.sleep(max(0.0, args.delay * random.uniform(0.6, 1.4)))

    if args.success:
        port = random.randint(40000, 65000)
        write_line(path, host, f"Accepted password for {COMPROMISED_USER} from {ip} port {port} ssh2")
        write_line(path, host, f"pam_unix(sshd:session): session opened for user {COMPROMISED_USER} by (uid=0)")
    print("\n[simulator] Done. Watch the dashboard - the agent forwards these lines within a few seconds.")


def windows_logon(args) -> None:
    if os.name != "nt":
        sys.exit("[simulator] The windows-logon scenario only runs on Windows.")
    import ctypes
    from ctypes import wintypes

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi32.LogonUserW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    advapi32.LogonUserW.restype = wintypes.BOOL
    logon32_logon_network, logon32_provider_default = 3, 0

    if args.windows_user != SIM_WINDOWS_USER:
        print(f"[simulator] WARNING: targeting '{args.windows_user}'. If that account exists and an account "
              "lockout policy is set, it may be locked out.")
    print(f"[simulator] {args.attempts} real failed logons for '{args.windows_user}' on this machine, ~{args.delay}s apart\n")

    for attempt in range(1, args.attempts + 1):
        token = wintypes.HANDLE()
        password = f"wrong-password-{random.randint(1000, 9999)}"
        ok = advapi32.LogonUserW(args.windows_user, ".", password, logon32_logon_network, logon32_provider_default, ctypes.byref(token))
        if ok:  # should never happen with a made-up password, but never leak a handle
            ctypes.windll.kernel32.CloseHandle(token)
            print(f"  attempt {attempt}: unexpectedly succeeded - stopping")
            return
        print(f"  attempt {attempt}: logon failed (Windows error {ctypes.get_last_error()}) - logged as event 4625 if logon-failure auditing is on")
        time.sleep(max(0.0, args.delay * random.uniform(0.6, 1.4)))
    print("\n[simulator] Done. An elevated agent will forward the 4625 events from the Security log.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Play a simulated attack in real time for IntelliSOC demos")
    parser.add_argument("--scenario", choices=["ssh-brute-force", "windows-logon"], default="ssh-brute-force")
    parser.add_argument("--attempts", type=int, default=12, help="Failed attempts (the brute-force threshold is 10)")
    parser.add_argument("--delay", type=float, default=1.5, help="Average seconds between attempts")
    parser.add_argument("--ip", default=DEFAULT_IP, help="Attacker IP, or 'random' (use for repeat runs: "
                        "an open alert for the same IP suppresses duplicates for 30 minutes)")
    parser.add_argument("--host", default=socket.gethostname(), help="Host name written into the log lines")
    parser.add_argument("--output", default=DEFAULT_LOG, help="Log file to append to (must be watched by the agent)")
    parser.add_argument("--no-success", dest="success", action="store_false",
                        help="Do not finish the SSH attack with a successful login")
    parser.add_argument("--windows-user", default=SIM_WINDOWS_USER, help="Account name for the windows-logon scenario")
    args = parser.parse_args()

    if args.scenario == "windows-logon":
        windows_logon(args)
    else:
        ssh_brute_force(args)


if __name__ == "__main__":
    main()
