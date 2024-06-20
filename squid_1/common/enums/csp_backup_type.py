from enum import Enum


class CSPBackupType(Enum):
    # used for CSPBackup, and CSP asset "backupInfo" type
    NATIVE_BACKUP = "NATIVE_BACKUP"
    HPE_CLOUD_BACKUP = "HPE_CLOUD_BACKUP"
    STAGING_BACKUP = "STAGING_BACKUP"
    TRANSIENT_BACKUP = "TRANSIENT_BACKUP"
