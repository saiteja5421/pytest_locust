from enum import Enum


# Specifies whether this is crash consistent or application consistent backup.
class BackupConsistency(Enum):
    CRASH = "CRASH"
    APPLICATION = "APPLICATION"
