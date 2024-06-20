from enum import Enum


class CSPK8sRefreshStatus(Enum):
    ok = "OK"
    warning = "WARNING"
    error = "ERROR"
    unknown = "UNKNOWN"
