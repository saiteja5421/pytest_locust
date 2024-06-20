from enum import Enum


class HealthState(Enum):
    OK = "SO_HEALTH_STATE_OK"
    WARNING = "SO_HEALTH_STATE_WARNING"
    CRITICAL = "SO_HEALTH_STATE_CRITICAL"
    UNKNOWN = "SO_HEALTH_STATE_UNKNOWN"
    ERROR = "SO_HEALTH_STATE_ERROR"
    REGISTERING = "SO_HEALTH_STATE_REGISTERING"
    DELETING = "SO_HEALTH_STATE_DELETING"


class HealthStatus(Enum):
    CONNECTED = "SO_HEALTH_STATUS_CONNECTED"
    DISCONNECTED = "SO_HEALTH_STATUS_DISCONNECTED"

