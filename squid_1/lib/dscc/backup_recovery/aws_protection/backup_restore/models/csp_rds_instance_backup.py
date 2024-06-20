from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
import datetime
from typing import Optional
from uuid import UUID
from common.enums.backup_state import BackupState
from common.enums.csp_backup_type import CSPBackupType
from common.enums.status import Status
from common.enums.trigger_type import TriggerType
from lib.dscc.backup_recovery.aws_protection.backup_restore.models.csp_backup import (
    AccountInfo,
    ProtectionPolicyInfoBackup,
    ScheduleInfo,
)
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    AssetInfo,
    ProtectionJobInfo,
)
from lib.dscc.backup_recovery.aws_protection.common.models.rds_common_objects import RDSBackupCSPInfo


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
    account_info: AccountInfo
    asset_info: AssetInfo
    backup_type: CSPBackupType
    csp_info: RDSBackupCSPInfo
    expires_at: datetime
    point_in_time: datetime
    protection_job_info: ProtectionJobInfo
    protection_policy_info: ProtectionPolicyInfoBackup
    schedule_info: ScheduleInfo
    start_time: datetime
    state: BackupState
    state_reason: str
    status: Status
    trigger_type: TriggerType
    type: Optional[str] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPRDSInstanceBackupList:
    count: int
    limit: int
    offset: int
    total: int
    items: list[CSPRDSInstanceBackup]
