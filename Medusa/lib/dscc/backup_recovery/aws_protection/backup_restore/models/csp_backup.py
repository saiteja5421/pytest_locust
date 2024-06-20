from typing import Optional
from uuid import UUID

from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase

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


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VolumeAttachmentInfo:
    device_name: str
    volume_details: VolumeDetails


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


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPBackupList:
    items: list[CSPBackup]
    count: int
    offset: int
    total: int
