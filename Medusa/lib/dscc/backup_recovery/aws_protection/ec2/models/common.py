from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
import datetime
from datetime import timezone
from google.protobuf.timestamp_pb2 import Timestamp
from uuid import UUID

from lib.common.enums.schedule_status import ScheduleStatus
from lib.common.enums.csp_backup_type import CSPBackupType


# The minimum representation of an object relationship according to
# https://pages.github.hpe.com/cloud/storage-design/docs/api.html#relationship-representation
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectReference:
    resource_uri: str
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectReferenceWithId:
    id: UUID
    resource_uri: str
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectReferenceWithName:
    name: str
    resource_uri: str
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectReferenceWithIdAndName:
    id: UUID
    name: str
    resource_uri: str
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VolumeAttachment:
    attached_to: ObjectReferenceWithIdAndName
    device: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class BackupCount:
    count: int
    backup_type: CSPBackupType


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AssetProtectionJobScheduleInfo:
    schedule_id: int
    status: ScheduleStatus
    updated_at: datetime

    def __init__(
        self,
        schedule_id: int,
        status: ScheduleStatus,
        updated_at: str,
    ):
        self.schedule_id = schedule_id
        self.status = ScheduleStatus(status)
        self.updated_at = rfc3339_string_to_datetime(updated_at)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AssetProtectionJobInfo:
    asset_info: ObjectReference
    protection_policy_info: ObjectReferenceWithName
    resource_uri: str
    schedule_info: list[AssetProtectionJobScheduleInfo]
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionGroupProtectionJobInfo:
    protection_policy_info: ObjectReferenceWithName
    resource_uri: str
    type: str


def rfc3339_string_to_datetime(rfc3339_str: str) -> datetime:
    """
    Converts a string in the format used by the DSCC REST API (e.g. '2023-01-13T01:13:45.305801Z')
    into a datetime.
    """
    if not rfc3339_str:
        return None
    timestamp = Timestamp()
    timestamp.FromJsonString(rfc3339_str)
    return timestamp.ToDatetime().replace(tzinfo=timezone.utc)
