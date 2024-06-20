import datetime
from uuid import UUID
from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ObjectIdName,
)
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.common import EmailNameObject, Attachment


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class IndexedEmail:
    attachments: list[Attachment]
    cc_recipients: list[EmailNameObject]
    # "from" is the keyword, hence used "_from" - might have to revisit this later
    _from: EmailNameObject
    id: UUID
    mail_folder_info: ObjectIdName
    received_at: datetime
    subject: str
    to_recipients: list[EmailNameObject]
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class IndexedEmailList:
    items: list[IndexedEmail]
    count: int
    offset: int
    total: int
