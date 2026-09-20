#!/usr/bin/env python
"""Mini-SOC endpoint agent entrypoint.

    collect -> parse -> normalize -> send

Usage:
    MINISOC_AGENT_ID=<id> MINISOC_AGENT_KEY=<key> python agent.py [--once] [--replay]

Register an agent first (as an admin user, via the backend API or Swagger
UI at /docs):
    POST /api/agents/register  {"name": "demo-collector", "hostname": "demo-host"}
This returns an id and api_key. Export them as MINISOC_AGENT_ID and
MINISOC_AGENT_KEY - never hard-code them in this repository.
"""
import argparse
import os
import socket
import sys
import time

import yaml

from collector import FileCollector
from normalizer import normalize
from parser import parse_line
from sender import BackendSender


def load_config(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


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

    poll_interval = config.get("poll_interval_seconds", 5)
    batch_size = config.get("batch_size", 200)

    print(f"[soc-agent] Starting. Watching {len(watched)} file(s). Backend: {config['backend_url']}")

    while True:
        for entry in watched:
            path = os.path.join(base_dir, entry["path"])
            source_type = entry["source_type"]

            raw_lines = collector.read_new_lines(path)
            if not raw_lines:
                continue

            events = []
            for line in raw_lines:
                parsed = parse_line(line, source_type)
                normalized = normalize(parsed, source=source_name)
                if normalized:
                    events.append(normalized)

            for i in range(0, len(events), batch_size):
                batch = events[i : i + batch_size]
                ok = sender.send_batch(batch)
                status = "sent" if ok else "FAILED to send"
                print(f"[soc-agent] {status} {len(batch)} event(s) from {entry['path']}")

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
