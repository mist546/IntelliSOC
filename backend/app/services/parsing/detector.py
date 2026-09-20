import re

AUTH_LOG_HINT = re.compile(r"sshd\[|sudo:|pam_unix")
APACHE_ACCESS_HINT = re.compile(r'"\w+ \S+ HTTP/\d\.\d"')
NGINX_ERROR_HINT = re.compile(r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2} \[\w+\]")
APACHE_ERROR_HINT = re.compile(r"^\[\w{3} \w{3} \d{1,2} \d{2}:\d{2}:\d{2}")


def detect_source_type(filename: str, content: str) -> str:
    name = filename.lower()
    if name.endswith(".csv"):
        return "CSV"
    if name.endswith(".json"):
        return "JSON"

    sample = "\n".join(content.splitlines()[:30])

    if "auth" in name or AUTH_LOG_HINT.search(sample):
        return "AUTH_LOG"
    if "nginx" in name and "error" in name:
        return "NGINX_ERROR"
    if "nginx" in name:
        return "NGINX_ACCESS"
    if "apache" in name and "error" in name:
        return "APACHE_ERROR"
    if "apache" in name or "access" in name:
        return "APACHE_ACCESS"

    if APACHE_ACCESS_HINT.search(sample):
        return "APACHE_ACCESS"
    if NGINX_ERROR_HINT.search(sample):
        return "NGINX_ERROR"
    if APACHE_ERROR_HINT.search(sample):
        return "APACHE_ERROR"
    if sample.strip().startswith("{") or sample.strip().startswith("["):
        return "JSON"
    if "," in sample.splitlines()[0] if sample.splitlines() else False:
        return "CSV"

    return "SYSLOG"
