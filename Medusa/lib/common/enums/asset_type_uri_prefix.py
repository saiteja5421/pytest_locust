from enum import Enum


class AssetTypeURIPrefix(Enum):
    API_V1 = "/api/v1"
    V1_BETA1 = "v1beta1"
    BACKUP_RECOVERY = "backup-recovery"
    VIRTUALIZATION = "virtualization"
    HYBRID_CLOUD_V1_BETA1 = f"/hybrid-cloud/{V1_BETA1}"
    BACKUP_RECOVERY_V1_BETA1 = f"/{BACKUP_RECOVERY}/{V1_BETA1}"
    VIRTUALIZATION_V1_BETA1 = f"/{VIRTUALIZATION}/{V1_BETA1}"

    # Add /api/v1 or update the reference to HYBRID_CLOUD_V1_BETA1 here
    # Remove after transition to PROD
    MACHINE_INSTANCES_RESOURCE_URI_PREFIX = f"{API_V1}/csp-machine-instances/"
    VOLUMES_RESOURCE_URI_PREFIX = f"{API_V1}/csp-volumes/"
    RDS_INSTANCES_RESOURCE_URI_PREFIX = f"{BACKUP_RECOVERY_V1_BETA1}/csp-rds-instances/"
    RDS_INSTANCES_RESOURCE_URI_PREFIX_HYBRID_CLOUD = f"{HYBRID_CLOUD_V1_BETA1}/csp-rds-instances/"
    PROTECTION_GROUPS_RESOURCE_URI_PREFIX = f"{BACKUP_RECOVERY_V1_BETA1}/csp-protection-groups/"
    PROTECTION_JOBS_RESOURCE_URI_PREFIX = f"{API_V1}/protection-jobs/"
    ACCOUNTS_RESOURCE_URI_PREFIX = f"{API_V1}/csp-accounts/"

    ACCOUNTS_RESOURCE_URI_PREFIX_V1BETA1 = f"{VIRTUALIZATION_V1_BETA1}/csp-accounts/"
