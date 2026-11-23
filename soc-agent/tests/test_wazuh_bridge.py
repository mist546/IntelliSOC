"""The Wazuh bridge: alerts.json lines are forwarded as raw JSON, and file
offsets are only committed once a batch has been delivered.

Run from the soc-agent folder with the backend's venv (it has pytest):
    ..\\backend\\.venv\\Scripts\\python.exe -m pytest tests
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import forward_file  # noqa: E402
from collector import FileCollector  # noqa: E402


class FakeSender:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.wazuh_batches: list[list[dict]] = []
        self.event_batches: list[list[dict]] = []

    def send_wazuh_alerts(self, alerts):
        if self.fail:
            return False
        self.wazuh_batches.append(alerts)
        return True

    def send_batch(self, events):
        if self.fail:
            return False
        self.event_batches.append(events)
        return True


def _alert(i: int) -> str:
    return json.dumps({"timestamp": "2026-11-09T14:10:00.123+0500", "rule": {"id": "5760"}, "agent": {"name": f"vm{i}"}})


def _write(path: Path, lines: list[str]) -> None:
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.writelines(line + "\n" for line in lines)


def _forward(collector, sender, path, batch_size=200, source_type="WAZUH_ALERTS"):
    forward_file(collector, sender, str(path), source_type, "bridge", batch_size, "alerts.json")


def test_alerts_are_forwarded_raw_and_invalid_lines_skipped(tmp_path):
    alerts = tmp_path / "alerts.json"
    _write(alerts, [_alert(1), "not json", _alert(2)])
    sender = FakeSender()

    _forward(FileCollector(str(tmp_path / "state.json")), sender, alerts)

    assert [a["agent"]["name"] for a in sender.wazuh_batches[0]] == ["vm1", "vm2"]
    assert sender.event_batches == []


def test_offset_not_committed_when_send_fails(tmp_path):
    alerts = tmp_path / "alerts.json"
    state = tmp_path / "state.json"
    _write(alerts, [_alert(1), _alert(2)])

    _forward(FileCollector(str(state)), FakeSender(fail=True), alerts)

    # A fresh collector (as after a restart) still sees both lines.
    sender = FakeSender()
    _forward(FileCollector(str(state)), sender, alerts)
    assert len(sender.wazuh_batches[0]) == 2


def test_offset_committed_after_successful_send(tmp_path):
    alerts = tmp_path / "alerts.json"
    state = tmp_path / "state.json"
    _write(alerts, [_alert(1)])
    collector = FileCollector(str(state))
    _forward(collector, FakeSender(), alerts)

    _write(alerts, [_alert(2)])
    sender = FakeSender()
    _forward(FileCollector(str(state)), sender, alerts)
    assert [a["agent"]["name"] for a in sender.wazuh_batches[0]] == ["vm2"]


def test_backlog_is_sent_in_batches(tmp_path):
    alerts = tmp_path / "alerts.json"
    _write(alerts, [_alert(i) for i in range(5)])
    sender = FakeSender()

    _forward(FileCollector(str(tmp_path / "state.json")), sender, alerts, batch_size=2)

    assert [len(b) for b in sender.wazuh_batches] == [2, 2, 1]


def test_plain_log_files_still_parsed_and_normalized(tmp_path):
    log = tmp_path / "auth.log"
    _write(log, ["Jan 12 10:15:23 web01 sshd[2345]: Failed password for root from 203.0.113.55 port 51234 ssh2"])
    sender = FakeSender()

    _forward(FileCollector(str(tmp_path / "state.json")), sender, log, source_type="AUTH_LOG")

    event = sender.event_batches[0][0]
    assert (event["event_type"], event["source_ip"], event["source"]) == ("AUTH_FAILURE", "203.0.113.55", "bridge")
