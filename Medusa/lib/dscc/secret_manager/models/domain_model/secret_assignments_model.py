import datetime
from dataclasses import dataclass

from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.secret_manager.common.models.common_secret_objects import ObjectNameUriId

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ObjectNameResourceTypeId,
    ObjectId,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
# NOTE# label attribute given in the spec but not in application response
class SecretAssignmentsModel:
    customer_id: str
    service: str
    id: str
    name: str
    type: str
    resource_uri: str
    generation: int
    updated_at: datetime
    created_at: datetime
    groups: list[ObjectNameUriId]
    status: str
    status_updated_at: datetime
    goal: str
    goal_updated_at: datetime
    secret: ObjectNameResourceTypeId
    appliance: ObjectId


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SecretAgreementsListModel:
    items: list[SecretAssignmentsModel]
    page_limit: int
    page_offset: int
    total: int
