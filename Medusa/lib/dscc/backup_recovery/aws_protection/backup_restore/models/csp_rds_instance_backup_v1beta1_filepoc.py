from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase
import datetime
from typing import Optional
from uuid import UUID
from lib.common.enums.backup_state import BackupState
from lib.common.enums.csp_backup_type import CSPBackupType
from lib.common.enums.status import Status
from lib.common.enums.trigger_type import TriggerType
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    AssetInfo,
    ObjectReferenceWithId,
    ProtectionJobInfo,
    ObjectNameResourceType,
)
from lib.dscc.backup_recovery.aws_protection.common.models.rds_common_objects import RDSBackupCSPInfo
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_rds_backup_model import (
    CSPRDSInstanceBackupModel,
    CSPRDSInstanceBackupListModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ScheduleInfo:
    name: str
    recurrence: str
    schedule_id: int
    job_id: Optional[UUID] = field(default=None)
    protection_group_id: Optional[UUID] = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPRDSInstanceBackup:
    created_at: datetime
    customer_id: str
    generation: int
    id: UUID
    name: str
    resource_uri: str
    updated_at: datetime
    account_info: ObjectReferenceWithId
    asset_info: AssetInfo
    backup_type: CSPBackupType
    csp_info: RDSBackupCSPInfo
    expires_at: datetime
    point_in_time: datetime
    protection_job_info: ProtectionJobInfo
    protection_policy_info: ObjectNameResourceType
    schedule_info: ScheduleInfo
    start_time: datetime
    state: BackupState
    state_reason: str
    status: Status
    trigger_type: TriggerType
    type: Optional[str] = None

    def to_domain_model(self):
        return CSPRDSInstanceBackupModel(
            id=self.id,
            name=self.name,
            backup_type=self.backup_type,
            csp_info=self.csp_info,
            expires_at=self.expires_at,
            point_in_time=self.point_in_time,
            state=self.state,
            status=self.status,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPRDSInstanceBackupList:
    count: int
    limit: int
    offset: int
    total: int
    items: list[CSPRDSInstanceBackup]

    def to_domain_model(self):
        return CSPRDSInstanceBackupListModel(
            items=[item.to_domain_model() for item in self.items],
            count=self.count,
            limit=self.limit,
            offset=self.offset,
            total=self.total,
        )
