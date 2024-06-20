from enum import Enum


class AssetTypeURIPrefix(Enum):
    API_V1 = "/api/v1"
    HYBRID_CLOUD_V1_BETA1 = "/hybrid-cloud/v1beta1"

    # Add /api/v1 or update the reference to HYBRID_CLOUD_V1_BETA1 here
    # Remove after transition to PROD
    MACHINE_INSTANCES_RESOURCE_URI_PREFIX = f"{API_V1}/csp-machine-instances/"
    VOLUMES_RESOURCE_URI_PREFIX = f"{API_V1}/csp-volumes/"
    RDS_INSTANCES_RESOURCE_URI_PREFIX = "/backup-recovery/v1beta1/csp-rds-instances/"
    RDS_INSTANCES_RESOURCE_URI_PREFIX_HYBRID_CLOUD = "/hybrid-cloud/v1beta1/csp-rds-instances/"
    PROTECTION_GROUPS_RESOURCE_URI_PREFIX = f"{API_V1}/csp-protection-groups/"
    PROTECTION_JOBS_RESOURCE_URI_PREFIX = f"{API_V1}/protection-jobs/"
    ACCOUNTS_RESOURCE_URI_PREFIX = f"{API_V1}/csp-accounts/"

    # Add hybrid-cloud/v1beta1 here
    ACCOUNTS_RESOURCE_URI_PREFIX_V1BETA1 = f"{HYBRID_CLOUD_V1_BETA1}/csp-accounts/"
