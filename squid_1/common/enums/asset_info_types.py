from enum import Enum


class AssetType(Enum):
    # Standard across atlantia
    CSP_RDS_DATABASE_INSTANCE = "hybrid-cloud/csp-rds-instances"
    CSP_K8S_APPLICATION = "CSP_K8S_APPLICATION"
    VOLUME_PROTECTION_GROUP = "VOLUME_PROTECTION_GROUP"
    CSP_MACHINE_INSTANCE = "hybrid-cloud/csp-machine-instance"
    CSP_PROTECTION_GROUP = "backup-recovery/csp-protection-group"
    CSP_MACHINE_INSTANCE_VIRTUALIZATION = "virtualization/csp-machine-instance"
    CSP_VOLUME_VIRTUALIZATION = "virtualization/csp-volume"
    CSP_TAG = "hybrid-cloud/csp-tag"
    CSP_TAG_KEY = "hybrid-cloud/csp-tag-key"
    CSP_VOLUME = "hybrid-cloud/csp-volume"
    MS365_USER = "backup-recovery/ms365-user"
    # MS365_PROTECTION_GROUP = "hybrid-cloud/ms365-protection-group"
    MS365_PROTECTION_GROUP = "backup-recovery/ms365-protection-group"

    @classmethod
    def members(cls):
        return list(map(lambda c: c.value, cls))
