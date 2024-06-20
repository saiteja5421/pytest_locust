from dataclasses import InitVar, dataclass, field
from dataclasses_json import dataclass_json, LetterCase
from uuid import UUID
from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.backup_consistency import BackupConsistency

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import ObjectIdType

"""
https://pages.github.hpe.com/cloud/storage-api/backup-recovery/v1beta1/index.html#tag/Protection-Jobs
asset_info {
    id
    type
}
overrides {
    protections [
        backup_schedule {
            id
            schedules [
                scheduleId
                consistency
            ]
        }
        cloud_schedule {
            id
            schedules [
                scheduleId
                consistency
            ]
        }
    ]
}
protection_policy_id
"""


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostProtectionJobs:
    asset_id: InitVar[UUID]
    asset_type: InitVar[str]
    protection_policy_id: UUID
    backup_id: InitVar[UUID]
    cloud_backup_id: InitVar[UUID]
    consistency: InitVar[str] = BackupConsistency.CRASH.value
    overrides: dict = field(default_factory=dict)
    asset_info: dict = field(default_factory=dict)

    def __post_init__(self, asset_id: UUID, asset_type: str, backup_id: UUID, cloud_backup_id: UUID, consistency: str):
        self.overrides.update({"protections": list()})
        if backup_id:
            backup_schedule = {
                "id": backup_id,
                "schedules": [{"scheduleId": 1}],
            }
            self.overrides["protections"].extend([backup_schedule])
            if asset_type == AssetType.CSP_MACHINE_INSTANCE.value:
                backup_schedule["schedules"][0]["consistency"] = consistency
        if cloud_backup_id:
            cloud_schedule = {
                "id": cloud_backup_id,
                "schedules": [{"scheduleId": 2}],
            }
            self.overrides["protections"].extend([cloud_schedule])
            if asset_type == AssetType.CSP_MACHINE_INSTANCE.value:
                cloud_schedule["schedules"][0]["consistency"] = consistency
        self.asset_info.update({"id": asset_id, "type": asset_type})


"""
From: https://pages.github.hpe.com/cloud/storage-api/#post-/protection-jobs

asset_info {                            REQ
    id                                  REQ
    type
}
effectiveFromDateTime : UTC
overrides {
    protections [{
        copy_pool_id
        id                              REQ
        schedules [{
            backup_granularity
            consistency
            expires_after {
                unit
                value
            }
            id                          REQ
            lock_for {
                unit
                value
            }
            name_pattern {
                format
            }
            verify
            vmwareOptions {
                include_rdm_disks
            }
        }]
    }]
}
protection_policy_id                    REQ
NOTE: the "protection" and "schedule" ID values are only required if a protection override is provided
"""


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostProtectionJob_NoOverrides:
    asset_info: ObjectIdType
    protection_policy_id: UUID
