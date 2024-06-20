import datetime
from uuid import UUID
from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ObjectIdName,
)
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.common import EmailNameObject, Attachment
from lib.dscc.backup_recovery.ms365_protection.common.enums.recurrence import Recurrence


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class IndexedEvent:
    all_day_event: bool
    attachments: list[Attachment]
    attendees: list[EmailNameObject]
    calender_info: ObjectIdName
    ends_at: datetime
    id: UUID
    organizer_info: EmailNameObject
    reoccurrence: Recurrence
    starts_at: datetime
    subject: str
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class IndexedEventList:
    items: list[IndexedEvent]
    count: int
    offset: int
    total: int
