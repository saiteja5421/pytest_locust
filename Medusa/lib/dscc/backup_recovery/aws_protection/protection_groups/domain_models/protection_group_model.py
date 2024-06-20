from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    CSPTag,
    ObjectNameResourceType,
)
from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.protection_group_dynamic_filter_type import ProtectionGroupDynamicFilterType


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class DynamicMemberFilterModel:
    cspTags: list[CSPTag]
    filterType: ProtectionGroupDynamicFilterType


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionJobInfoModel:
    protectionPolicyInfo: ObjectNameResourceType
    resourceUri: str
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionGroupModel:
    customerId: str
    generation: int
    id: str
    name: str
    resourceUri: str
    type: str
    assetType: AssetType
    assetCount: int
    protectionJobInfo: list[ProtectionJobInfoModel]


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionGroupListModel:
    items: list[ProtectionGroupModel]
    count: int
    offset: int
    total: int
