"""Windows events are not lost when the backend is down, and auth.log lines
with RFC 3339 timestamps (Ubuntu 23.10+) are parsed like classic ones.

Run from the soc-agent folder with the backend's venv (it has pytest):
    ..\\backend\\.venv\\Scripts\\python.exe -m pytest tests
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import forward_windows_events  # noqa: E402
from parser import parse_line  # noqa: E402
from windows_collector import EVENT_NS, WindowsEventCollector  # noqa: E402


class FakeWevtutilCollector(WindowsEventCollector):
    """Serves failed-logon events with the given record IDs instead of
    calling wevtutil, honouring the EventRecordID> filter and /c: limit."""

    def __init__(self, state_file: str, record_ids: list[int]) -> None:
        super().__init__("Security", [4625], state_file)
        self.record_ids = record_ids

    def _wevtutil(self, *args: str) -> str:
        count = int(next(a for a in args if a.startswith("/c:"))[3:])
        if "/rd:true" in args:
            selected = sorted(self.record_ids, reverse=True)[:count]
        else:
            selected = [r for r in sorted(self.record_ids) if r > self.last_record_id][:count]
        events = "".join(
            f"<Event xmlns='{EVENT_NS}'><System><Provider Name='Microsoft-Windows-Security-Auditing'/>"
            f"<EventID>4625</EventID><TimeCreated SystemTime='2026-09-25T18:25:55.6264255Z'/>"
            f"<EventRecordID>{r}</EventRecordID><Channel>Security</Channel><Computer>WS01</Computer>"
            f"</System><EventData><Data Name='TargetUserName'>administrator</Data>"
            f"<Data Name='LogonType'>3</Data><Data Name='IpAddress'>203.0.113.55</Data></EventData></Event>"
            for r in selected
        )
        return f"<Events>{events}</Events>"


class FakeSender:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.batches: list[list[dict]] = []

    def send_batch(self, events):
        if self.fail:
            return False
        self.batches.append(events)
        return True


def _collector(tmp_path, record_ids, bookmark=100):
    state = tmp_path / "windows_state.json"
    if bookmark is not None:
        state.write_text(json.dumps({"Security": bookmark}))
    return FakeWevtutilCollector(str(state), record_ids)


def test_windows_bookmark_not_advanced_when_send_fails(tmp_path):
    forward_windows_events(_collector(tmp_path, [101, 102]), FakeSender(fail=True), batch_size=200)

    # After a restart the same events are read again.
    sender = FakeSender()
    forward_windows_events(_collector(tmp_path, [101, 102], bookmark=None), sender, batch_size=200)
    assert len(sender.batches[0]) == 2


def test_windows_bookmark_advanced_after_delivery(tmp_path):
    forward_windows_events(_collector(tmp_path, [101, 102]), FakeSender(), batch_size=200)
    assert json.loads((tmp_path / "windows_state.json").read_text()) == {"Security": 102}

    sender = FakeSender()
    forward_windows_events(_collector(tmp_path, [101, 102, 103], bookmark=None), sender, batch_size=200)
    assert len(sender.batches) == 1 and len(sender.batches[0]) == 1


def test_windows_backlog_sent_in_batches(tmp_path):
    sender = FakeSender()
    forward_windows_events(_collector(tmp_path, list(range(101, 106))), sender, batch_size=2)
    assert [len(b) for b in sender.batches] == [2, 2, 1]


def test_windows_first_start_begins_at_newest_record(tmp_path):
    sender = FakeSender()
    forward_windows_events(_collector(tmp_path, [7, 8, 9], bookmark=None), sender, batch_size=200)
    assert sender.batches == []
    assert json.loads((tmp_path / "windows_state.json").read_text()) == {"Security": 9}


def test_rfc3339_auth_line_is_parsed():
    event = parse_line(
        "2026-11-09T14:10:00.123456+05:00 ubuntu-web01 sshd[4100]: "
        "Failed password for invalid user admin from 203.0.113.55 port 51200 ssh2",
        "AUTH_LOG",
    )
    assert event["event_type"] == "AUTH_FAILURE"
    assert (event["username"], event["source_ip"], event["host"]) == ("admin", "203.0.113.55", "ubuntu-web01")
    assert event["timestamp"] == "2026-11-09T09:10:00.123456+00:00"


def test_rfc3339_variants():
    accepted = "ubuntu-web01 sshd[1]: Accepted password for root from 203.0.113.55 port 22 ssh2"
    for ts, expected in [
        ("2026-11-09T09:10:00Z", "2026-11-09T09:10:00+00:00"),
        ("2026-11-09T14:10:00.1234567+0500", "2026-11-09T09:10:00.123456+00:00"),
    ]:
        event = parse_line(f"{ts} {accepted}", "AUTH_LOG")
        assert event["event_type"] == "AUTH_SUCCESS"
        assert event["timestamp"] == expected


def test_classic_auth_line_still_parsed():
    event = parse_line("Jan 12 10:15:23 web01 sshd[2345]: Failed password for root from 203.0.113.55 port 51234 ssh2", "AUTH_LOG")
    assert event["event_type"] == "AUTH_FAILURE" and event["host"] == "web01"
