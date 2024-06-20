from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    CSPTag,
    ObjectNameResourceType,
    ObjectNameResourceTypeId,
    ObjectReferenceWithId,
)
from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.csp_type import CspType
from lib.common.enums.protection_group_dynamic_filter_type import ProtectionGroupDynamicFilterType
from lib.dscc.backup_recovery.aws_protection.protection_groups.domain_models.protection_group_model import (
    DynamicMemberFilterModel,
    ProtectionGroupListModel,
    ProtectionGroupModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class DynamicMemberFilter:
    cspTags: list[CSPTag]
    filterType: ProtectionGroupDynamicFilterType

    @staticmethod
    def from_domain_model(domain_model: DynamicMemberFilterModel):
        return DynamicMemberFilter(cspTags=domain_model.cspTags, filterType=domain_model.filterType)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionJobInfo:
    protectionPolicyInfo: ObjectNameResourceType
    resourceUri: str
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionGroup:
    customerId: str
    generation: int
    id: str
    name: str
    resourceUri: str
    type: str
    accounts: list[ObjectNameResourceTypeId]
    assetType: AssetType
    createdAt: str
    description: str
    membershipType: str
    assetCount: int
    protectionJobInfo: list[ProtectionJobInfo]
    cspRegions: list[str]
    updatedAt: str
    dynamicMemberFilter: DynamicMemberFilter
    cspType: CspType
    subscriptions: list[ObjectReferenceWithId]

    def to_domain_model(self):
        return ProtectionGroupModel(
            customerId=self.customerId,
            generation=self.generation,
            id=self.id,
            name=self.name,
            assetType=self.assetType,
            assetCount=self.assetCount,
            protectionJobInfo=self.protectionJobInfo,
            resourceUri=self.resourceUri,
            type=self.type,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionGroupList:
    items: list[ProtectionGroup]
    count: int
    offset: int
    total: int

    def to_domain_model(self):
        return ProtectionGroupListModel(
            items=[item.to_domain_model() for item in self.items],
            count=self.count,
            offset=self.offset,
            total=self.total,
        )
