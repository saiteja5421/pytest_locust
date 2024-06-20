import datetime
from uuid import UUID
from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ObjectNameResourceType,
    ObjectNameResourceTypeId,
)
from lib.common.enums.protection_group_membership_type import ProtectionGroupMembershipType
from typing import Optional


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class DynamicMemberFilter:
    filter_type: str
    filters: list[UUID]


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MS365ProtectionJobInfo:
    protection_policy_info: ObjectNameResourceType
    resource_uri: str
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MS365CSPProtectionGroup:
    created_at: datetime
    customer_id: str
    generation: int
    id: UUID
    name: str
    resource_uri: str
    type: str
    updated_at: datetime
    console_uri: str
    asset_count: int
    asset_type: str
    description: str
    dynamic_member_filter: DynamicMemberFilter
    membership_type: ProtectionGroupMembershipType
    accounts: list[ObjectNameResourceTypeId]
    csp_regions: list[str]
    protection_job_info: list[MS365ProtectionJobInfo]


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MS365CSPProtectionGroupList:
    items: list[MS365CSPProtectionGroup]
    count: int
    offset: int
    total: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MS365CSPProtectionGroupCreate:
    asset_type: str
    membership_type: ProtectionGroupMembershipType
    name: str
    description: Optional[str] = None
    dynamic_member_filter: Optional[DynamicMemberFilter] = None
    staticMember_ids: Optional[UUID] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MS365CSPProtectionGroupUpdate:
    description: str
    name: str
    static_members_added: Optional[UUID] = None
    static_members_removed: Optional[UUID] = None
