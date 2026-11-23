#!/usr/bin/env python
"""Mini-SOC endpoint agent entrypoint.

    collect -> parse -> normalize -> send

Collects from two kinds of source every poll:
  * text log files it tails (e.g. /var/log/auth.log, or the live file
    written by scripts/simulate_attack.py), and
  * on Windows, the live Windows event log (Security channel by default;
    needs an elevated terminal) - see windows_collector.py.
It also sends a heartbeat so the dashboard can show it as online.

A watched file with source_type WAZUH_ALERTS (a Wazuh manager's
/var/ossec/logs/alerts/alerts.json) is forwarded as raw JSON alerts to
POST /api/events/wazuh instead - see config.wazuh.yaml.

Usage:
    MINISOC_AGENT_ID=<id> MINISOC_AGENT_KEY=<key> python agent.py [--once] [--replay]

Register an agent first (as an admin user, via the backend API or Swagger
UI at /docs):
    POST /api/agents/register  {"name": "demo-collector", "hostname": "demo-host"}
This returns an id and api_key. Export them as MINISOC_AGENT_ID and
MINISOC_AGENT_KEY - never hard-code them in this repository.
"""
import argparse
import json
import os
import socket
import sys
import time

import yaml

from collector import FileCollector
from normalizer import normalize
from parser import parse_line
from sender import BackendSender
from windows_collector import WindowsEventCollector, is_supported_platform


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def make_windows_collector(config: dict, base_dir: str, replay: bool) -> WindowsEventCollector | None:
    settings = config.get("windows_event_log") or {}
    if not settings.get("enabled"):
        return None
    if not is_supported_platform():
        print("[soc-agent] windows_event_log is enabled but this is not Windows - skipping it.")
        return None
    collector = WindowsEventCollector(
        channel=settings.get("channel", "Security"),
        event_ids=settings.get("event_ids", [4624, 4625]),
        state_file=os.path.join(base_dir, settings.get("state_file", "windows_state.json")),
    )
    if replay:
        collector.reset()
    return collector


def to_wazuh_alerts(lines: list[str]) -> list[dict]:
    alerts = []
    for line in lines:
        try:
            alert = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(alert, dict):
            alerts.append(alert)
    return alerts


def forward_file(collector, sender, path: str, source_type: str, source_name: str, batch_size: int, label: str) -> None:
    """Sends a file's new lines one batch at a time, committing the read
    offset only after each batch is delivered. On failure the rest is left
    for the next poll, so nothing is lost or sent twice."""
    while True:
        lines = collector.read_new_lines(path, max_lines=batch_size)
        if not lines:
            return

        if source_type == "WAZUH_ALERTS":
            payload = to_wazuh_alerts(lines)
            ok = sender.send_wazuh_alerts(payload)
        else:
            payload = [e for e in (normalize(parse_line(line, source_type), source=source_name) for line in lines) if e]
            ok = sender.send_batch(payload)

        if not ok:
            print(f"[soc-agent] FAILED to send {len(payload)} event(s) from {label}; will retry next poll")
            return
        collector.commit(path)
        if payload:
            print(f"[soc-agent] sent {len(payload)} event(s) from {label}")
        if len(lines) < batch_size:
            return


def forward_windows_events(windows, sender, batch_size: int) -> None:
    """Same delivery guarantee as forward_file, for the Windows event log:
    the bookmark only advances once a batch has been delivered."""
    label = f"Windows {windows.channel} log"
    while True:
        events = windows.read_new_events(max_events=batch_size)
        if not windows.records_read:
            return
        if not sender.send_batch(events):
            print(f"[soc-agent] FAILED to send {len(events)} event(s) from {label}; will retry next poll")
            return
        windows.commit()
        if events:
            print(f"[soc-agent] sent {len(events)} event(s) from {label}")
        if windows.records_read < batch_size:
            return


def run(config_path: str, once: bool, replay: bool) -> int:
    config = load_config(config_path)

    agent_id = os.environ.get("MINISOC_AGENT_ID")
    agent_key = os.environ.get("MINISOC_AGENT_KEY")
    if not agent_id or not agent_key:
        print("ERROR: MINISOC_AGENT_ID and MINISOC_AGENT_KEY environment variables are required.")
        print("Register an agent via POST /api/agents/register and export the returned credentials.")
        return 1

    base_dir = os.path.dirname(os.path.abspath(config_path))
    state_file = os.path.join(base_dir, config.get("state_file", "state.json"))
    collector = FileCollector(state_file)
    sender = BackendSender(config["backend_url"], agent_id, agent_key)
    source_name = socket.gethostname()

    watched = config.get("watched_files", [])
    if replay:
        for entry in watched:
            collector.reset(os.path.join(base_dir, entry["path"]))
        print("[soc-agent] Replay mode: offsets reset, all watched files will be resent from the start.")

    windows = make_windows_collector(config, base_dir, replay)

    poll_interval = config.get("poll_interval_seconds", 2)
    batch_size = config.get("batch_size", 200)
    heartbeat_interval = config.get("heartbeat_interval_seconds", 30)
    last_heartbeat = 0.0

    print(f"[soc-agent] Starting. Watching {len(watched)} file(s). Backend: {config['backend_url']}")
    if windows:
        print(f"[soc-agent] Collecting live Windows '{windows.channel}' events: IDs {windows.event_ids}")

    while True:
        if time.monotonic() - last_heartbeat >= heartbeat_interval:
            sender.send_heartbeat()
            last_heartbeat = time.monotonic()

        for entry in watched:
            path = os.path.join(base_dir, entry["path"])
            forward_file(collector, sender, path, entry["source_type"], source_name, batch_size, entry["path"])

        if windows:
            try:
                forward_windows_events(windows, sender, batch_size)
            except PermissionError as exc:
                print(f"[soc-agent] {exc}")
                print("[soc-agent] Windows event collection disabled for this run; file collection continues.")
                windows = None
            except Exception as exc:  # noqa: BLE001 - keep collecting files even if the event log fails
                print(f"[soc-agent] Windows event log read failed: {exc}")

        if once:
            return 0
        time.sleep(poll_interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mini-SOC endpoint collector agent")
    parser.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "config.yaml"))
    parser.add_argument("--once", action="store_true", help="Run a single collection pass and exit (useful for demos)")
    parser.add_argument("--replay", action="store_true", help="Reset offsets and resend all watched files from the start")
    args = parser.parse_args()

    sys.exit(run(args.config, once=args.once, replay=args.replay))
