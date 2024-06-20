import datetime
from uuid import UUID
from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.common import (
    ObjectIdResourceType,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MS365GroupInfo:
    description: str
    email_address: str
    ms365_id: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MS365CSPGroup:
    created_at: datetime
    customer_id: str
    generation: int
    id: UUID
    name: str
    resource_uri: str
    type: str
    updated_at: datetime
    account_info: ObjectIdResourceType
    csp_info: MS365GroupInfo
    csp_type: str
    csp_id: str = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MS365CSPGroupList:
    items: list[MS365CSPGroup]
    count: int
    offset: int
    total: int
