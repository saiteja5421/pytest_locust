from enum import Enum


class AuditState(Enum):
    SUCCESS = "Success"
    FAILURE = "Failure"
    PERMISSION_DENIED = "PermissionDenied"
    INITIATED = "Initiated"
