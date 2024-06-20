from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase
from uuid import UUID

import datetime
from datetime import timezone
from google.protobuf.timestamp_pb2 import Timestamp
from typing import Any, Optional

from common.enums.schedule_status import ScheduleStatus


# Added this class because the attributes are all lower case
# as opposed to the Tag class under /model/aws
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPTag:
    key: str
    value: str


@dataclass
class ObjectIdUriType:
    id: str
    uri: str
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectIdResourceUriType:
    id: str
    resourceUri: str
    type: str


# The minimum representation of an object relationship according to
# https://pages.github.hpe.com/cloud/storage-design/docs/api.html#relationship-representation
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectReferenceWithId:
    id: str
    resourceUri: str
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectReference:
    resourceUri: str
    type: str


# This object is used for "ProtectionPolicyInfo", "ProtectionGroupInfo" and "AttachedTo",
# which all contain "name:str, resourceUri:str, type:str"
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectNameResourceType:
    name: str
    resourceUri: str
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectNameResourceTypeId:
    name: str
    resource_uri: str
    type: str
    id: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectUnitValue:
    unit: str
    value: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AttachmentInfo:
    attachedTo: ObjectNameResourceType
    device: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionInfo:
    protectionGroups: list[Any]
    lastBackedUpAt: None


"""
For responses like below which are generally present inside other objects
{
   "subnet":{
      "id":"subnet-0dd602c4923fe8b21"
   },
   "vpc":{
      "id":"vpc-0b7b3134bbfa06732"
   }
}
"""


@dataclass
class ObjectId:
    id: str


@dataclass
class ObjectName:
    name: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RefreshInfo:
    last_refreshed_at: str
    status: str


"""
For responses like below (Tag Keys):
{
   "items":[
      "Test1",
      "Test2"
   ]
}
"""


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ItemList:
    items: list[str]


"""
Can be used for a generic object like the one shown below
{
   "securityGroups":[
      {
         "id":"sg-0aafd909fa0b27dd4",
         "name":"launch-wizard-21"
      }
   ]
}
"""


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectIdName:
    id: str
    name: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectCspIdName:
    cspId: str
    cspName: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ScheduleInfo:
    scheduleId: int
    status: ScheduleStatus
    updatedAt: datetime

    def __init__(
        self,
        scheduleId: int,
        status: ScheduleStatus,
        updatedAt: str,
    ):
        self.scheduleId = scheduleId
        self.status = ScheduleStatus(status)
        self.updatedAt = rfc3339_string_to_datetime(updatedAt)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionJobInfo:
    resourceUri: str
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectCountType:
    count: int
    backupType: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectResourceUri:
    resource_uri: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectIdType:
    id: UUID
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ErrorResponse:
    error: str
    errorCode: str
    traceId: str


# https://pages.github.hpe.com/cloud/storage-design/docs/architecture/api.html#error-responses
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class GLCPErrorResponse:
    debugId: str
    errorCode: str
    httpStatusCode: int
    message: str


@dataclass
class CopyPoolInfo:
    id: UUID
    name: str
    type: str
    region: Optional[str] = field(default=None)


@dataclass
class NamePattern:
    format: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ActiveTime:
    active_from_time: str
    active_until_time: str


@dataclass
class RepeatInterval:
    every: int
    on: Optional[list[int]] = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Schedule:
    recurrence: str
    repeatInterval: RepeatInterval
    startTime: str = ""
    activeTime: Optional[ActiveTime] = field(default=None)


@dataclass
class AssetInfo:
    type: str
    id: Optional[UUID] = field(default=None)
    resourceUri: Optional[str] = field(default=None)
    displayName: Optional[str] = field(default=None)
    name: Optional[str] = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TagKeyValue:
    key: str
    values: ItemList


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


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostScriptInfo:
    hostId: str = field(default=None)
    params: str = field(default=None)
    path: str = field(default=None)
    timeout_in_seconds: int = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PreScriptInfo:
    hostId: str = field(default=None)
    params: str = field(default=None)
    path: str = field(default=None)
    timeout_in_seconds: int = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CspProtectionJobInfo:
    asset_info: AssetInfo
    protection_policy_info: ObjectNameResourceType
    resource_uri: str
    schedule_info: list[ScheduleInfo]
    type: str
