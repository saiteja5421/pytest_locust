from typing import Optional

from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VolumeDetailsModel:
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
class VolumeAttachmentInfoModel:
    device_name: str
    volume_details: VolumeDetailsModel


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPBackupModel:
    backup_type: str
    consistency: str
    id: str
    name: str
    state: str
    status: str
    index_status: str
    resource_uri: str
    volume_attachment_info: Optional[list[VolumeAttachmentInfoModel]] = None
    point_in_time: Optional[str] = ""
    created_at: Optional[str] = ""
    expires_at: Optional[str] = ""


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPBackupListModel:
    items: list[CSPBackupModel]
    count: int
    offset: int
    total: int
