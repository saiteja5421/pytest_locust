from enum import Enum


class CSPBackupMode(Enum):
    # The mode of K8sApplication Backup.
    OPTIMIZED = "OPTIMIZED"
    INCREMENTAL = "INCREMENTAL"
