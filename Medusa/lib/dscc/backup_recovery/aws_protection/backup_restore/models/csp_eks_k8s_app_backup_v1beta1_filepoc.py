from dataclasses import dataclass
from typing import Optional
from dataclasses_json import dataclass_json, LetterCase
from uuid import UUID
from lib.common.enums.csp_backup_mode import CSPBackupMode
from lib.common.enums.backup_consistency import BackupConsistency
from lib.common.enums.trigger_type import TriggerType
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_eks_k8s_app_backup_model import (
    CSPK8sAppBackupInfoModel,
    CSPK8sAppBackupListModel,
)
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ObjectNameResourceType,
    ObjectReference,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EKSScheduleInfo:
    name: str
    recurrence: str
    schedule_id: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sAppBackupInfo:
    id: UUID
    name: str
    generation: int
    description: str
    customer_id: str
    account_id: UUID
    csp_account_id: str
    asset_id: UUID
    cluster_id: str
    backup_region: str
    backup_mode: CSPBackupMode
    backup_type: str
    consistency: BackupConsistency
    start_time: str
    protection_job_info: ObjectReference
    protection_policy_info: ObjectNameResourceType
    schedule_info: EKSScheduleInfo
    state: str
    state_reason: str
    status: str
    trigger_type: TriggerType
    resource_uri: str
    type: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    locked_until: Optional[str] = None
    expires_at: Optional[str] = None

    def to_domain_model(self):
        return CSPK8sAppBackupInfoModel(
            id=self.id,
            state=self.state,
            status=self.status,
            backup_type=self.backup_type,
            expires_at=self.expires_at,
            locked_until=self.locked_until,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sAppBackupList:
    items: list[CSPK8sAppBackupInfo]
    count: int
    offset: int
    total: int

    def to_domain_model(self):
        return CSPK8sAppBackupListModel(total=self.total, items=[item.to_domain_model() for item in self.items])
