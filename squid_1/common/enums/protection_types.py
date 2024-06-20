from enum import Enum


class ProtectionType(Enum):
    SNAPSHOT = "SNAPSHOT"
    BACKUP = "BACKUP"
    CLOUD_BACKUP = "CLOUD_BACKUP"
