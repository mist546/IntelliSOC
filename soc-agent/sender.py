"""Sends batches of normalized events to the Mini-SOC backend, authenticating
with the agent's registered credentials (never hard-coded; read from
environment variables by agent.py)."""
import time

import requests


class BackendSender:
    def __init__(self, backend_url: str, agent_id: str, agent_key: str, timeout: int = 15) -> None:
        self.events_url = f"{backend_url.rstrip('/')}/api/events"
        self.wazuh_url = f"{backend_url.rstrip('/')}/api/events/wazuh"
        self.heartbeat_url = f"{backend_url.rstrip('/')}/api/agents/heartbeat"
        self.headers = {"X-Agent-Id": agent_id, "X-Agent-Key": agent_key}
        self.timeout = timeout

    def send_batch(self, events: list[dict], max_retries: int = 3) -> bool:
        if not events:
            return True
        return self._post(self.events_url, {"events": events}, max_retries)

    def send_wazuh_alerts(self, alerts: list[dict], max_retries: int = 3) -> bool:
        """Forwards raw Wazuh alerts (lines of alerts.json); the backend parses them."""
        if not alerts:
            return True
        return self._post(self.wazuh_url, {"alerts": alerts}, max_retries)

    def _post(self, url: str, payload: dict, max_retries: int) -> bool:
        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.post(url, json=payload, headers=self.headers, timeout=self.timeout)
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

    def send_heartbeat(self) -> bool:
        """Tells the backend this agent is alive even when no new logs arrive.
        A single attempt: a missed heartbeat is simply retried next interval."""
        try:
            resp = requests.post(self.heartbeat_url, headers=self.headers, timeout=self.timeout)
        except requests.RequestException as exc:
            print(f"[soc-agent] Heartbeat failed: {exc}")
            return False
        if resp.status_code != 200:
            print(f"[soc-agent] Heartbeat rejected ({resp.status_code}): {resp.text[:200]}")
            return False
        return True
