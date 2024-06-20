class Paths:
    AWS_ACCOUNTS = "/virtualization/v1beta1/csp-accounts"
    CSP_MACHINE_INSTANCES = "/virtualization/v1beta1/csp-machine-instances"
    CSP_MACHINE_INSTANCE_BACKUPS = "/backup-recovery/v1beta1/csp-machine-instance-backups"
    CSP_VOLUMES = "/virtualization/v1beta1/csp-volumes"
    CSP_VOLUME_BACKUPS = "/backup-recovery/v1beta1/csp-volume-backups"
    CSP_ACCOUNTS = "/virtualization/v1beta1/csp-accounts"
    EC2_INSTANCES = "/virtualization/v1beta1/csp-machine-instances"
    EBS_VOLUMES = "/virtualization/v1beta1/csp-volumes"
    PROTECTION_JOBS = "/backup-recovery/v1beta1/protection-jobs"
    PROTECTION_GROUPS = "/backup-recovery/v1beta1/csp-protection-groups"
    PROTECTION_POLICIES = "/backup-recovery/v1beta1/protection-policies"
    TEST_API = (
        "/test/v1/nb-rest.cam"  # Test api url is for testing purpose only.Here using it for unregistering account
    )
    COPY2CLOUD_API = "/test/v1/nb-rest.dataprotection/copy2cloud"
    TASK_API = "api/v1/tasks"


class ConfigPaths:
    CONFIG_FILE_PATH = "/workspaces/Squid/config.yml"
    LOCUST_CONF_PATH = "/workspaces/Squid/tests/locust.conf"


class RDSPaths:
    CSP_RDS_INSTANCES = "/virtualization/v1beta1/csp-rds-instances"
    CSP_RDS_ACCOUNTS = "/virtualization/v1beta1/csp-rds-accounts"
    CSP_RDS_INSTANCES_BACKUPS = "/backup-recovery/v1beta1/csp-rds-instance-backups"


class GFRSPaths:
    CSP_MACHINE_INSTANCES = "csp-machine-instances"
    CSP_MACHINE_INSTANCES_BACKUPS = "csp-machine-instance-backups"
    CSP_VOLUMES = "csp-volumes"
    CSP_VOLUMES_BACKUPS = "csp-volume-backups"
    BACKUPS = "backups"
    INDEX_FILES = "index-files"
    INDEXED_FILES = "indexed-files"
    INDEXED_FILESYSTEMS = "indexed-filesystems"
    RESTORE_FILES = "restore-files"
    GET_VOLUME_INDEXED_FILE = "csp-volume"
    GET_INSTANCE_INDEXED_FILE = "csp-machine-instance"
    GET_VIRTUAL_MACHINE_INDEXED_FILE = "virtual-machine"
