import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.parsing.auth_log import parse_auth_log
from app.services.parsing.detector import detect_source_type
from app.services.parsing.structured import parse_csv, parse_json_logs
from app.services.parsing.web_log import parse_access_log


def test_parse_valid_failed_password_line():
    line = "Jan 12 10:15:23 webserver01 sshd[2345]: Failed password for root from 203.0.113.55 port 51234 ssh2"
    events = parse_auth_log(line)
    assert len(events) == 1
    e = events[0]
    assert e.event_type == "AUTH_FAILURE"
    assert e.username == "root"
    assert e.source_ip == "203.0.113.55"
    assert e.host == "webserver01"


def test_parse_accepted_login_line():
    line = "Jan 12 10:16:01 webserver01 sshd[2345]: Accepted password for root from 203.0.113.55 port 51290 ssh2"
    events = parse_auth_log(line)
    assert events[0].event_type == "AUTH_SUCCESS"
    assert events[0].status == "success"


def test_parse_malformed_line_does_not_crash():
    events = parse_auth_log("this is not a valid syslog line at all")
    assert len(events) == 1
    assert events[0].event_type == "UNPARSED"


def test_parse_empty_content():
    assert parse_auth_log("") == []
    assert parse_auth_log("\n\n\n") == []


def test_parse_missing_ip_and_username():
    line = "Jan 12 10:16:01 webserver01 sshd[2345]: pam_unix(sshd:auth): authentication failure"
    events = parse_auth_log(line)
    assert len(events) == 1
    assert events[0].source_ip is None


def test_parse_invalid_timestamp_falls_back():
    line = "NotADate webserver01 sshd[1]: Failed password for root from 1.2.3.4 port 22 ssh2"
    events = parse_auth_log(line)
    assert len(events) == 1  # still parsed, just with fallback timestamp handling


def test_parse_access_log_extracts_ip_and_path():
    line = '203.0.113.10 - - [12/Jan/2026:10:20:15 +0000] "GET /index.php?id=1 HTTP/1.1" 200 512 "-" "Mozilla/5.0"'
    events = parse_access_log(line, source_type="APACHE_ACCESS")
    assert len(events) == 1
    assert events[0].source_ip == "203.0.113.10"
    assert "GET" in events[0].message


def test_parse_csv():
    content = "timestamp,source_ip,username,event_type,message\n2026-01-12T10:00:00,1.2.3.4,bob,AUTH_FAILURE,failed login\n"
    events = parse_csv(content)
    assert len(events) == 1
    assert events[0].source_ip == "1.2.3.4"
    assert events[0].event_type == "AUTH_FAILURE"


def test_parse_json_list():
    content = '[{"source_ip": "5.6.7.8", "event_type": "HTTP_REQUEST", "message": "GET /"}]'
    events = parse_json_logs(content)
    assert len(events) == 1
    assert events[0].source_ip == "5.6.7.8"


def test_detect_source_type_auth_log():
    content = "Jan 12 10:15:23 host sshd[1]: Failed password for root from 1.2.3.4 port 22 ssh2"
    assert detect_source_type("auth.log", content) == "AUTH_LOG"


def test_detect_source_type_csv_by_extension():
    assert detect_source_type("events.csv", "a,b,c\n1,2,3") == "CSV"
