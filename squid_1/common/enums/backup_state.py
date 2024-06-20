from enum import Enum


class BackupState(Enum):
    OK = "OK"
    ERROR = "ERROR"
    CREATING = "CREATING"
    DELETING = "DELETING"
    UPDATING = "UPDATING"
    DELETE_PENDING = "DELETE_PENDING"
    IN_USE_FOR_RESTORE = "IN_USE_FOR_RESTORE"
    MOUNTED = "MOUNTED"
    SUCCESS = "Success"
    DELETED = "DELETED"
    AVAILABLE = "Available"
