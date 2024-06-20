import datetime
from uuid import UUID
from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ObjectNameResourceType,
)
from common.enums.protection_group_membership_type import ProtectionGroupMembershipType
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
    organizations: list[UUID]
    protection_job_info: list[MS365ProtectionJobInfo]

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, MS365CSPProtectionGroup)
            and (self.created_at == other.created_at)
            and (self.customer_id == other.customer_id)
            and (self.generation == other.generation)
            and (self.id == other.id)
            and (self.name == other.name)
            and (self.resource_uri == other.resource_uri)
            and (self.type == other.type)
            and (self.updated_at == other.updated_at)
            and (self.console_uri == other.console_uri)
            and (self.asset_count == other.asset_count)
            and (self.asset_type == other.asset_type)
            and (self.description == other.description)
            and (self.dynamic_member_filter == other.dynamic_member_filter)
            and (self.membership_type == other.membership_type)
            and (len(self.organizations) == len(other.organizations))
            and {x.to_json() for x in self.organizations}
            == {x.to_json() for x in other.organizations}
            and (len(self.protection_job_info) == len(other.protection_job_info))
            and {x.to_json() for x in self.protection_job_info}
            == {x.to_json() for x in other.protection_job_info}
        )


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
    static_member_ids: Optional[UUID] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class MS365CSPProtectionGroupUpdate:
    description: str
    name: str
    static_members_added: Optional[UUID] = None
    static_members_removed: Optional[UUID] = None
