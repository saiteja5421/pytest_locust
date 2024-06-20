from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from typing import Optional
from datetime import datetime

from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.protection_group_membership_type import ProtectionGroupMembershipType
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import CSPTag

from lib.dscc.backup_recovery.aws_protection.protection_groups.models.protection_group_v1beta1_filepoc import (
    DynamicMemberFilter,
)
from lib.dscc.backup_recovery.aws_protection.protection_groups.domain_models.csp_protection_group_payload_model import (
    PatchCustomProtectionGroupModel,
    PostCustomProtectionGroupModel,
    PostCustomProtectionGroupStaticMembersModel,
    PostDynamicProtectionGroupModel,
    PostUpdateCSPTagsModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PatchCustomProtectionGroup:
    name: str
    description: str

    @staticmethod
    def from_domain_model(domain_model: PatchCustomProtectionGroupModel):
        return PatchCustomProtectionGroup(name=domain_model.name, description=domain_model.description)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostCustomProtectionGroupStaticMembers:
    static_members_added: Optional[list[str]] = None
    static_members_removed: Optional[list[str]] = None

    @staticmethod
    def from_domain_model(domain_model: PostCustomProtectionGroupStaticMembersModel):
        return PostCustomProtectionGroupStaticMembers(
            static_members_added=domain_model.static_members_added,
            static_members_removed=domain_model.static_members_removed,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostCustomProtectionGroup:
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

    @staticmethod
    def from_domain_model(domain_model: PostCustomProtectionGroupModel):
        return PostCustomProtectionGroup(
            account_ids=domain_model.account_ids,
            asset_type=domain_model.asset_type,
            name=domain_model.name,
            csp_regions=domain_model.csp_regions,
            static_member_ids=domain_model.static_member_ids,
            membership_type=domain_model.membership_type,
            description=domain_model.description,
            subscription_ids=domain_model.subscription_ids,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostDynamicProtectionGroup:
    account_ids: list[str]
    name: str
    csp_regions: list[str]
    dynamic_member_filter: DynamicMemberFilter
    asset_type: AssetType
    membership_type: str = ProtectionGroupMembershipType.DYNAMIC.value
    description: str = (
        f"Automatic protection group created by the Medusa framework on {datetime.now().strftime('%D %H:%M:%S')}"
    )
    subscription_ids: list[str] = None

    @staticmethod
    def from_domain_model(domain_model: PostDynamicProtectionGroupModel):
        dynamic_member_filter: DynamicMemberFilter = DynamicMemberFilter.from_domain_model(
            domain_model=domain_model.dynamic_member_filter
        )
        return PostDynamicProtectionGroup(
            account_ids=domain_model.account_ids,
            name=domain_model.name,
            csp_regions=domain_model.csp_regions,
            dynamic_member_filter=dynamic_member_filter,
            asset_type=domain_model.asset_type,
            membership_type=domain_model.membership_type,
            description=domain_model.description,
            subscription_ids=domain_model.subscription_ids,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostUpdateCSPTags:
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

    @staticmethod
    def from_domain_model(domain_model: PostUpdateCSPTagsModel):
        return PostUpdateCSPTags(
            csp_tags_added=domain_model.csp_tags_added, csp_tags_removed=domain_model.csp_tags_removed
        )
