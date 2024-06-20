from enum import Enum


class CSPItemsType(Enum):
    CSP_ACCOUNT = "hybrid-cloud/csp-account"
    CSP_MACHINE_INSTANCE_BACKUP = "backup-recovery/csp-machine-instance-backup"
    CSP_PROTECTION_POLICY = "backup-recovery/protection-policy"
    CSP_PROTECTION_JOB = "backup-recovery/protection-job"
