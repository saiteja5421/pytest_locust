from enum import Enum


class AtlantiaKafkaEvents(Enum):
    CSP_ACCOUNT_INFO_EVENT_TYPE = "csp.cloudaccountmanager.v1.CspAccountInfo"
    CSP_ACCOUNT_INFO_REPEAT_EVENT_TYPE = "csp.cloudaccountmanager.v1.CspAccountInfo.repeat"
    CSP_ACCOUNT_USE_BY_SERVICE_EVENT_TYPE = "csp.cloudaccountmanager.v1.CspAccountUseByService"
    SYNC_ACCOUNT_EVENT_TYPE = "csp.inventory.v1.SyncAccountRequest"
    SYNC_ASSET_EVENT_TYPE = "csp.inventory.v1.SyncAssetsRequest"
    ACCOUNT_SYNC_INFO_EVENT_TYPE = "csp.inventory.v1.AccountSyncInfo"
    CSP_ACCOUNT_SYNC_INFO_EVENT_TYPE = "csp.cloudaccountmanager.v1.AccountSyncInfo"
    ASSET_STATE_INFO_EVENT_TYPE = "csp.inventory.v1.AssetStateInfo"
    ATLAS_POLICY_JOB_CREATE_EVENT_TYPE = "com.hpe.storagecentral.atlas-policy-job.create"
    ATLAS_POLICY_JOB_DELETE_EVENT_TYPE = "com.hpe.storagecentral.atlas-policy-job.delete"
    ATLAS_POLICY_UPDATE_EVENT_TYPE = "com.hpe.storagecentral.atlas-policy.update"
    ATLAS_POLICY_JOB_SUSPEND_EVENT_TYPE = "com.hpe.storagecentral.atlas-policy-job.suspend"
    ATLAS_POLICY_JOB_RESUME_EVENT_TYPE = "com.hpe.storagecentral.atlas-policy-job.resume"
    SCHEDULER_PROTECTION_JOB_CREATE_EVENT_TYPE = "csp.scheduler.v1.ProtectionJobCreate"
    SCHEDULER_PROTECTION_JOB_DELETE_EVENT_TYPE = "csp.scheduler.v1.ProtectionJobDelete"
    SCHEDULER_POLICY_UPDATE_EVENT_TYPE = "csp.scheduler.v1.AtlasPolicyUpdate"
    SCHEDULER_PROTECTION_JOB_RESUME_EVENT_TYPE = "csp.scheduler.v1.ProtectionJobResume"
    SCHEDULER_PROTECTION_JOB_SUSPEND_EVENT_TYPE = "csp.scheduler.v1.ProtectionJobSuspend"
    ATLAS_POLICY_JOB_RUN_EVENT_TYPE = "com.hpe.storagecentral.atlas-policy-job.run"
    REPORT_INSTANCE_CREATE_EVENT_TYPE = "com.hpe.storagecentral.csp_machine_instances.create"
    REPORT_INSTANCE_UPDATE_EVENT_TYPE = "com.hpe.storagecentral.csp_machine_instances.update"
    REPORT_INSTANCE_DELETE_EVENT_TYPE = "com.hpe.storagecentral.csp_machine_instances.delete"
    REPORT_VOLUME_CREATE_EVENT_TYPE = "com.hpe.storagecentral.csp_volumes.create"
    REPORT_VOLUME_UPDATE_EVENT_TYPE = "com.hpe.storagecentral.csp_volumes.update"
    REPORT_VOLUME_DELETE_EVENT_TYPE = "com.hpe.storagecentral.csp_volumes.delete"
    BACKUP_CREATION_EVENT_TYPE = "com.hpe.storagecentral.dataprotection.backup.cloudbackup.created"
    BACKUP_DELETION_EVENT_TYPE = "com.hpe.storagecentral.dataprotection.backup.cloudbackup.deleted"
    PROTECTION_JOB_CREATE = "OPERATION_PROTECTION_JOB_CREATE"
    PROTECTION_JOB_DELETE = "OPERATION_PROTECTION_JOB_DELETE"
    SCHEDULER_INITIATE_BACKUP_REQUEST = "csp.dataprotection.v1.InitiateBackupRequest"
    AUDIT_EVENT_TYPE = "audit.v1.AuditData"
    ATLAS_POLICY_JOB_ONPREM_CREATE_EVENT_TYPE = "com.hpe.storagecentral.atlas-policy-job.onprem.create"
    ATLAS_POLICY_ONPREM_UPDATE_EVENT_TYPE = "com.hpe.storagecentral.atlas-policy.onprem.update"
    ATLAS_POLICY_JOB_ONPREM_RESUME_EVENT_TYPE = "com.hpe.storagecentral.atlas-policy-job.onprem.resume"
