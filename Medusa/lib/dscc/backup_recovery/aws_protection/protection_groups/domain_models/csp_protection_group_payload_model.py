from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from typing import Optional
from datetime import datetime

from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.protection_group_membership_type import ProtectionGroupMembershipType
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import CSPTag
from lib.dscc.backup_recovery.aws_protection.protection_groups.domain_models.protection_group_model import (
    DynamicMemberFilterModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PatchCustomProtectionGroupModel:
    name: str
    description: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostCustomProtectionGroupStaticMembersModel:
    static_members_added: Optional[list[str]] = None
    static_members_removed: Optional[list[str]] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostCustomProtectionGroupModel:
    account_ids: list[str]
    asset_type: AssetType
    name: str
    csp_regions: list[str]
    static_member_ids: list[str]
    membership_type: str = ProtectionGroupMembershipType.STATIC.value
    description: str = (
        f"Custom protection group created by the Medusa framework on {datetime.now().strftime('%D %H:%M:%S')}"
    )
    subscription_ids: list[str] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostDynamicProtectionGroupModel:
    account_ids: list[str]
    name: str
    csp_regions: list[str]
    dynamic_member_filter: DynamicMemberFilterModel
    asset_type: AssetType
    membership_type: str = ProtectionGroupMembershipType.DYNAMIC.value
    description: str = (
        f"Automatic protection group created by the Medusa framework on {datetime.now().strftime('%D %H:%M:%S')}"
    )
    subscription_ids: list[str] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostUpdateCSPTagsModel:
    csp_tags_added: list[CSPTag] = None
    csp_tags_removed: list[str] = None
    """
    The json payload looks like this:
    {
      "cspTagsAdded":[
        {"key":"Key1","value":"Value1"},
        {"key":"Key2","value":"Value2"}
      ],
      "cspTagsRemoved":["Key3","Key4"]
    }
    """
