import uuid

from dataclasses import dataclass
from dataclasses_json import LetterCase, dataclass_json


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AuditResource:
    id: uuid.UUID
    type: str
    name: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AuditEvent:
    customer_id: int
    permission: str
    code: str
    state: str
    associated_resource: AuditResource


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AssetUpdateEvent:
    app_type: str
    generation: int
    name: str
    account_id: uuid.UUID
    csp_id: str
    region: str
    protection_status: str
    recovery_point_exists: bool
    policy_assigned: bool


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AssetDeleteEvent:
    app_type: str
    account_id: uuid.UUID
    csp_id: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AssetStateInfo:
    type: int
    id: uuid.UUID
    state: int
