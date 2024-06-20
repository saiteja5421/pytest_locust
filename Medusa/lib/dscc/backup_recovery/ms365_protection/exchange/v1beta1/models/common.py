import datetime
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ScheduleStatus,
    ObjectNameResourceType,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ObjectIdResourceType:
    id: str
    resource_uri: str
    type: str
    name: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MailBoxInfo:
    count: int
    size: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MS365UserEmailObject:
    email_address: str
    mail_box_info: MailBoxInfo
    ms365_id: str
    region: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MS365ScheduleInfo:
    id: int
    status: ScheduleStatus
    updatedAt: datetime = field(
        default=None,
        metadata=dict(
            encoder=lambda date: date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            decoder=lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ") if date else None,
        ),
    )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MS365ProtectionJobInfo:
    protection_policy_info: ObjectNameResourceType
    resource_uri: str
    schedule_info: list[MS365ScheduleInfo]
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MSCommonObjectInfo:
    id: str
    resource_uri: str
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MSBackupProtectionPolicyInfo:
    id: str
    name: str
    resource_uri: str
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MSBackupScheduleInfo:
    name: str
    recurrence: str
    schedule_id: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RestoreItem:
    item_id: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Attachment:
    attachment_type: str
    name: str
    size_in_bytes: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EmailNameObject:
    email_address: str
    name: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class LinkedResource:
    application_name: str
    display_name: str
    web_url: str
