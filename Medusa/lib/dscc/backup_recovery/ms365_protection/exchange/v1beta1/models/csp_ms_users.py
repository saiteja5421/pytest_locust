import datetime
from uuid import UUID
from dataclasses import dataclass, field
from typing import Optional
from dataclasses_json import dataclass_json, LetterCase
from lib.common.enums.state import State
from lib.common.enums.protection_summary import ProtectionStatus
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ObjectNameResourceTypeId,
    ObjectCountType,
)
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.common import (
    ObjectIdResourceType,
    MS365UserEmailObject,
    MS365ProtectionJobInfo,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MS365CSPUser:
    created_at: datetime
    customer_id: str
    generation: int
    id: UUID
    name: str
    type: str
    updated_at: datetime
    account_info: ObjectIdResourceType
    csp_info: MS365UserEmailObject
    csp_type: str
    protection_status: ProtectionStatus
    state: State
    csp_id: str
    resource_uri: Optional[str] = field(default=None)
    console_uri: Optional[str] = field(default=None)
    protection_group_info: list[ObjectNameResourceTypeId] = field(default=None)
    protection_job_info: list[MS365ProtectionJobInfo] = field(default_factory=list)
    backup_info: list[ObjectCountType] = field(default_factory=list)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MS365CSPUserList:
    items: list[MS365CSPUser]
    count: int
    offset: int
    total: int
