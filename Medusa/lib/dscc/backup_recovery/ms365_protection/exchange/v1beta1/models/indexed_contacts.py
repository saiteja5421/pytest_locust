from uuid import UUID
from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ObjectIdName,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class IndexedContact:
    contact_folder_info: ObjectIdName
    display_name: str
    email_address: str
    given_name: str
    id: UUID
    middle_name: str
    name: str
    nick_name: str
    surname: str
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class IndexedContactList:
    items: list[IndexedContact]
    count: int
    offset: int
    total: int
