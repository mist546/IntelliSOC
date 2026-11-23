"""Mapping of real Windows Security event XML (as produced by
`wevtutil qe Security /f:xml`) to the backend event schema.

Run from the soc-agent folder with the backend's venv (it has pytest):
    ..\\backend\\.venv\\Scripts\\python.exe -m pytest tests
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from windows_collector import event_xml_to_dict  # noqa: E402

NS = "http://schemas.microsoft.com/win/2004/08/events/event"


def _event(event_id: int, data: dict, record_id: int = 5001) -> ET.Element:
    fields = "".join(f"<Data Name='{k}'>{v}</Data>" for k, v in data.items())
    return ET.fromstring(
        f"<Event xmlns='{NS}'><System><Provider Name='Microsoft-Windows-Security-Auditing'/>"
        f"<EventID>{event_id}</EventID><TimeCreated SystemTime='2026-09-25T18:25:55.6264255Z'/>"
        f"<EventRecordID>{record_id}</EventRecordID><Channel>Security</Channel><Computer>WS01</Computer>"
        f"</System><EventData>{fields}</EventData></Event>"
    )


def test_failed_network_logon_keeps_remote_ip():
    event = event_xml_to_dict(_event(4625, {
        "SubjectUserName": "-", "TargetUserName": "administrator", "TargetDomainName": "WS01",
        "Status": "0xc000006d", "FailureReason": "%%2313", "SubStatus": "0xc000006a",
        "LogonType": "3", "WorkstationName": "KALI", "IpAddress": "203.0.113.55", "IpPort": "51234",
    }))
    assert event["event_type"] == "AUTH_FAILURE" and event["status"] == "failed"
    assert event["source_ip"] == "203.0.113.55" and event["username"] == "administrator"
    assert event["host"] == "WS01" and event["timestamp"] == "2026-09-25T18:25:55.626425+00:00"
    assert event["metadata"]["logon_type"] == 3 and event["metadata"]["local_logon"] is False
    assert event["message"].startswith("An account failed to log on: account WS01\\administrator")
    assert "<EventID>4625</EventID>" in event["raw_log"]


def test_local_failed_logon_is_attributed_to_loopback():
    event = event_xml_to_dict(_event(4625, {"TargetUserName": "alice", "LogonType": "2", "IpAddress": "-"}))
    assert event["source_ip"] == "127.0.0.1" and event["metadata"]["local_logon"] is True


def test_interactive_success_is_kept():
    event = event_xml_to_dict(_event(4624, {
        "TargetUserName": "alice", "TargetDomainName": "WS01", "LogonType": "10", "IpAddress": "198.51.100.7",
    }))
    assert event["event_type"] == "AUTH_SUCCESS" and event["source_ip"] == "198.51.100.7"


def test_routine_system_logons_are_filtered_out():
    assert event_xml_to_dict(_event(4624, {"TargetUserName": "SYSTEM", "TargetDomainName": "NT AUTHORITY", "LogonType": "5"})) is None
    assert event_xml_to_dict(_event(4624, {"TargetUserName": "WS01$", "TargetDomainName": "CORP", "LogonType": "3"})) is None
    assert event_xml_to_dict(_event(4624, {"TargetUserName": "DWM-1", "TargetDomainName": "Window Manager", "LogonType": "2"})) is None


def test_lockout_uses_target_account_and_no_fake_ip():
    event = event_xml_to_dict(_event(4740, {"TargetUserName": "bob", "SubjectUserName": "DC01$"}))
    assert event["event_type"] == "ACCOUNT_LOCKOUT" and event["username"] == "bob" and event["source_ip"] is None


def test_unknown_event_ids_are_passed_through_generically():
    event = event_xml_to_dict(_event(4799, {"TargetUserName": "Administrators"}))
    assert event["event_type"] == "WINDOWS_EVENT_4799"
