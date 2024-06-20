from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase

import datetime
from typing import Optional
from uuid import UUID
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ObjectIdName,
    ObjectNameResourceType,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class DualAuthOperation:
    checked_at: str
    customer_id: str
    description: str
    generation: int
    id: UUID
    name: str
    operation_resource: ObjectNameResourceType
    requested_at: datetime
    requested_by_email: str
    requested_by_uri: str
    requested_operation: str
    resource_uri: str
    source_service_external_name: str
    state: str
    type: str
    checked_by_email: Optional[str] = None  # Available only in the response of an authorized (approved/denied) request
    checked_by_uri: Optional[str] = None  # Available only in the response of an authorized (approved / denied) request
    groups: Optional[list[ObjectIdName]] = None  # Available only when fetching requests


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class DualAuthOperationList:
    items: list[DualAuthOperation]
    page_limit: int
    page_offset: int
    total: int
