from enum import Enum


class AssetType(Enum):
    # Standard across atlantia
    CSP_RDS_DATABASE_INSTANCE = "virtualization/csp-rds-instance"
    CSP_K8S_APPLICATION = "hybrid-cloud/csp-k8s-application"
    VOLUME_PROTECTION_GROUP = "backup-recovery/volume-protection-group"
    CSP_MACHINE_INSTANCE = "virtualization/csp-machine-instance"
    CSP_PROTECTION_GROUP = "backup-recovery/csp-protection-group"
    CSP_TAG = "hybrid-cloud/csp-tag"
    CSP_TAG_KEY = "hybrid-cloud/csp-tag-key"
    CSP_VOLUME = "virtualization/csp-volume"
    MS365_USER = "backup-recovery/ms365-user"
    MS365_PROTECTION_GROUP = "backup-recovery/ms365-protection-group"

    @classmethod
    def members(cls):
        return list(map(lambda c: c.value, cls))
