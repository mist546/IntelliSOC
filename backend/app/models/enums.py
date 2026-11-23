import enum


class Severity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, enum.Enum):
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    FALSE_POSITIVE = "FALSE_POSITIVE"


class IncidentStatus(str, enum.Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    CONTAINED = "CONTAINED"
    CLOSED = "CLOSED"


class InvestigationStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class UserRole(str, enum.Enum):
    ANALYST = "ANALYST"
    ADMIN = "ADMIN"


class SourceType(str, enum.Enum):
    AUTH_LOG = "AUTH_LOG"
    SYSLOG = "SYSLOG"
    APACHE_ACCESS = "APACHE_ACCESS"
    APACHE_ERROR = "APACHE_ERROR"
    NGINX_ACCESS = "NGINX_ACCESS"
    NGINX_ERROR = "NGINX_ERROR"
    CSV = "CSV"
    JSON = "JSON"
    WINDOWS_EVENT = "WINDOWS_EVENT"
    WAZUH = "WAZUH"
    UNKNOWN = "UNKNOWN"
