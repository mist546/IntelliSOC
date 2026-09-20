"""Sends batches of normalized events to the Mini-SOC backend, authenticating
with the agent's registered credentials (never hard-coded; read from
environment variables by agent.py)."""
import time

import requests


class BackendSender:
    def __init__(self, backend_url: str, agent_id: str, agent_key: str, timeout: int = 15) -> None:
        self.events_url = f"{backend_url.rstrip('/')}/api/events"
        self.headers = {"X-Agent-Id": agent_id, "X-Agent-Key": agent_key}
        self.timeout = timeout

    def send_batch(self, events: list[dict], max_retries: int = 3) -> bool:
        if not events:
            return True

        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.post(
                    self.events_url, json={"events": events}, headers=self.headers, timeout=self.timeout
                )
                if resp.status_code == 201:
                    return True
                if resp.status_code == 401:
                    print("[soc-agent] Authentication rejected by backend - check MINISOC_AGENT_ID/MINISOC_AGENT_KEY")
                    return False
                print(f"[soc-agent] Backend returned {resp.status_code}: {resp.text[:200]}")
            except requests.RequestException as exc:
                print(f"[soc-agent] Send attempt {attempt}/{max_retries} failed: {exc}")

            if attempt < max_retries:
                time.sleep(2**attempt)  # exponential backoff

        return False
