from typing import Optional
from uuid import UUID

from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.backup_recovery.aws_protection.backup_restore.domain_models.csp_backup_model import (
    CSPBackupListModel,
    CSPBackupModel,
    VolumeDetailsModel,
    VolumeAttachmentInfoModel,
)

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    AssetInfo,
    ProtectionJobInfo,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AccountInfo:
    id: UUID
    resource_uri: str
    type: str


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
class VolumeDetails:
    delete_on_termination: bool
    iops: int
    is_encrypted: bool
    kms_key_id: str
    snapshot_id: str
    throughput_in_mi_bps: int
    volume_id: str
    volume_size: int
    volume_type: str

    def to_domain_model(self):
        return VolumeDetailsModel(
            delete_on_termination=self.delete_on_termination,
            iops=self.iops,
            is_encrypted=self.is_encrypted,
            kms_key_id=self.kms_key_id,
            snapshot_id=self.snapshot_id,
            throughput_in_mi_bps=self.throughput_in_mi_bps,
            volume_id=self.volume_id,
            volume_size=self.volume_size,
            volume_type=self.volume_type,
        )

    @staticmethod
    def from_domain_model(domain_model: VolumeDetailsModel):
        return VolumeDetails(
            delete_on_termination=domain_model.delete_on_termination,
            iops=domain_model.iops,
            is_encrypted=domain_model.is_encrypted,
            kms_key_id=domain_model.kms_key_id,
            snapshot_id=domain_model.snapshot_id,
            throughput_in_mi_bps=domain_model.throughput_in_mi_bps,
            volume_id=domain_model.volume_id,
            volume_size=domain_model.volume_size,
            volume_type=domain_model.volume_type,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VolumeAttachmentInfo:
    device_name: str
    volume_details: VolumeDetails

    @staticmethod
    def from_domain_model(domain_model: VolumeAttachmentInfoModel):
        volume_details = VolumeDetails.from_domain_model(domain_model=domain_model.volume_details)
        return VolumeAttachmentInfo(device_name=domain_model.device_name, volume_details=volume_details)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionPolicyInfoBackup:
    name: str
    resourceUri: Optional[str] = field(default=None)
    type: Optional[str] = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPBackup:
    account_info: AccountInfo
    asset_info: AssetInfo
    backup_mode: str
    backup_type: str
    consistency: str
    customer_id: str
    description: str
    generation: int
    id: str
    name: str
    resource_uri: str
    state: str
    status: str
    trigger_type: str
    index_status: str
    type: str
    csp_type: str
    protection_job_info: ProtectionJobInfo
    protection_policy_info: ProtectionPolicyInfoBackup
    schedule_info: ScheduleInfo
    volume_attachment_info: Optional[list[VolumeAttachmentInfo]] = None
    point_in_time: Optional[str] = ""
    created_at: Optional[str] = ""
    imported_at: Optional[str] = ""
    expires_at: Optional[str] = ""
    updated_at: Optional[str] = ""
    started_at: Optional[str] = ""
    locked_until: Optional[str] = None

    def to_domain_model(self):
        return CSPBackupModel(
            backup_type=self.backup_type,
            consistency=self.consistency,
            id=self.id,
            name=self.name,
            state=self.state,
            status=self.status,
            resource_uri=self.resource_uri,
            index_status=self.index_status,
            volume_attachment_info=self.volume_attachment_info,
            point_in_time=self.point_in_time,
            created_at=self.created_at,
            expires_at=self.expires_at,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPBackupList:
    items: list[CSPBackup]
    count: int
    offset: int
    total: int

    def to_domain_model(self):
        return CSPBackupListModel(
            items=[item.to_domain_model() for item in self.items],
            count=self.count,
            offset=self.offset,
            total=self.total,
        )
