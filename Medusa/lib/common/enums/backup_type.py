from enum import Enum


class BackupType(Enum):
    # used for test code logic
    CLOUD_BACKUP = "CLOUD_BACKUP"
    BACKUP = "BACKUP"
    NATIVE_BACKUP = "NATIVE_BACKUP"
    SNAPSHOT = "SNAPSHOT"
    CLOUD_SNAPSHOT = "CLOUD_SNAPSHOT"
