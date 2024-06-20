from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from uuid import UUID

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    CSPTag,
    ObjectNameResourceType,
    ObjectNameResourceTypeId,
    ObjectReferenceWithId,
)
from common.enums.asset_info_types import AssetType
from common.enums.csp_type import CspType
from common.enums.protection_group_dynamic_filter_type import ProtectionGroupDynamicFilterType


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class DynamicMemberFilter:
    cspTags: list[CSPTag]
    filterType: ProtectionGroupDynamicFilterType

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, DynamicMemberFilter)
            and (self.filterType == other.filterType)
            and (len(self.cspTags) == len(other.cspTags))
            and {x.to_json() for x in self.cspTags} == {x.to_json() for x in other.cspTags}
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionJobInfo:
    protectionPolicyInfo: ObjectNameResourceType
    resourceUri: str
    type: str

    def __init__(
        self,
        protectionPolicyInfo: ObjectNameResourceType,
        resourceUri: str,
        type: str,
    ):
        self.protectionPolicyInfo = ObjectNameResourceType(**protectionPolicyInfo)
        self.resourceUri = resourceUri
        self.type = type


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionGroup:
    customerId: str
    generation: int
    id: str
    name: str
    resourceUri: str
    type: str
    consoleUri: str
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

    def __init__(
        self,
        customerId: str,
        generation: int,
        id: UUID,
        name: str,
        resourceUri: str,
        type: str,
        consoleUri: str,
        accounts: list[ObjectNameResourceTypeId],
        assetType: AssetType,
        createdAt: str,
        description: str,
        dynamicMemberFilter: DynamicMemberFilter,
        membershipType: str,
        assetCount: int,
        protectionJobInfo: list[ProtectionJobInfo],
        cspRegions: list[str],
        updatedAt: str,
        # "cspType" is present on FILEPOC.  "subscriptions" is not, but is mentioned in:
        # https://pages.github.hpe.com/cloud/storage-api/backup-recovery/v1beta1/index.html#tag/csp-protection-groups/operation/CSPProtectionGroupsGet
        # Neither are currently on SCDEV01
        cspType: CspType = None,
        subscriptions: list[ObjectReferenceWithId] = None,
    ):
        self.customerId = customerId
        self.generation = generation
        self.id = id
        self.name = name
        self.resourceUri = resourceUri
        self.type = type
        self.consoleUri = consoleUri
        self.accounts = [ObjectNameResourceTypeId for account in accounts] if accounts else accounts
        self.assetType = assetType
        self.createdAt = createdAt
        self.description = description
        self.dynamicMemberFilter = DynamicMemberFilter(**dynamicMemberFilter) if dynamicMemberFilter else None
        self.membershipType = membershipType
        self.assetCount = assetCount
        self.protectionJobInfo = (
            [ProtectionJobInfo(**protectionInfo) for protectionInfo in protectionJobInfo]
            if protectionJobInfo
            else protectionJobInfo
        )
        self.cspRegions = [region for region in cspRegions] if cspRegions else cspRegions
        self.updatedAt = updatedAt
        self.cspType = cspType
        self.subscriptions = (
            [ObjectReferenceWithId for subscription in subscriptions] if subscriptions else subscriptions
        )

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, ProtectionGroup)
            and (self.customerId == other.customerId)
            and (self.generation == other.generation)
            and (self.id == other.id)
            and (self.name == other.name)
            and (self.resourceUri == other.resourceUri)
            and (self.type == other.type)
            and (self.consoleUri == other.consoleUri)
            and (len(self.accounts) == len(other.accounts))
            and {x.to_json() for x in self.accounts} == {x.to_json() for x in other.accounts}
            and (self.assetType == other.assetType)
            and (self.createdAt == other.createdAt)
            and (self.description == other.description)
            and (self.dynamicMemberFilter == other.dynamicMemberFilter)
            and (self.membershipType == other.membershipType)
            and (self.assetCount == other.assetCount)
            and (len(self.protectionJobInfo) == len(other.protectionJobInfo))
            and {x.to_json() for x in self.protectionJobInfo} == {x.to_json() for x in other.protectionJobInfo}
            and (self.cspRegions == other.cspRegions)
            and (self.updatedAt == other.updatedAt)
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionGroupList:
    items: list[ProtectionGroup]
    count: int
    offset: int
    total: int

    def __init__(self, items: list[ProtectionGroup], count: int, offset: int, total: int) -> None:
        self.items = [ProtectionGroup(**item) for item in items] if items else items
        self.count = count
        self.offset = offset
        self.total = total
