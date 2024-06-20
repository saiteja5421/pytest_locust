from enum import Enum


# Current status of the K8sApplication backup.
class CSPK8sBackupStatus(Enum):
    OK = "OK"
    ERROR = "ERROR"
