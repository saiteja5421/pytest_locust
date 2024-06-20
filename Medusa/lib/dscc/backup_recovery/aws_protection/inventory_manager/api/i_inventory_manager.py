from typing import Protocol, Union, runtime_checkable
from uuid import UUID

from requests import Response
import requests
from lib.common.enums.asset_info_types import AssetType
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    GLCPErrorResponse,
    ItemList,
    TagKeyValue,
)
from lib.dscc.backup_recovery.aws_protection.ebs.domain_models.csp_volume_model import (
    CSPVolumeListModel,
    CSPVolumeModel,
)

from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_instance_model import (
    CSPMachineInstanceListModel,
    CSPMachineInstanceModel,
)
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_resource_group_model import (
    CSPResourceGroupListModel,
    CSPResourceGroupModel,
)
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_subnet_model import (
    CSPSubnetListModel,
    CSPSubnetModel,
)
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_subscription_model import (
    CSPSubscriptionListModel,
    CSPSubscriptionModel,
)
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_vpc_model import CSPVPCListModel, CSPVPCModel
from lib.dscc.backup_recovery.aws_protection.protection_groups.domain_models.protection_group_model import (
    ProtectionGroupListModel,
    ProtectionGroupModel,
)
from lib.dscc.backup_recovery.aws_protection.protection_groups.domain_models.csp_protection_group_payload_model import (
    PatchCustomProtectionGroupModel,
    PostCustomProtectionGroupStaticMembersModel,
    PostUpdateCSPTagsModel,
)


@runtime_checkable
class IInventoryManager(Protocol):
    def trigger_account_inventory_sync(
        self, account_id: str, expected_status_code: requests.codes = requests.codes.accepted
    ) -> Union[str, GLCPErrorResponse]: ...

    def get_csp_machine_instances(
        self,
        limit: int = 20,
        offset: int = 0,
        sort: str = "name",
        filter: str = "",
        tag_filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
        expected_error: str = "",
    ) -> Union[CSPMachineInstanceListModel, GLCPErrorResponse]: ...

    def get_csp_machine_instance_by_id(
        self,
        csp_machine_id: str,
        response_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPMachineInstanceModel, GLCPErrorResponse]: ...

    def trigger_csp_machine_instance_sync(self, csp_machine_id: str) -> Union[str, GLCPErrorResponse]: ...

    def get_trigger_csp_machine_instance_sync_response(self, csp_machine_id: str) -> Response: ...

    def get_csp_volumes(
        self,
        limit: int = 1000,
        offset: int = 0,
        sort: str = "name",
        filter: str = "",
        tag_filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
        expected_error: str = "",
    ) -> Union[CSPVolumeListModel, GLCPErrorResponse]: ...

    def get_csp_volume_by_id(
        self,
        csp_volume_id: str,
        response_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPVolumeModel, GLCPErrorResponse]: ...

    def trigger_csp_volume_sync(self, csp_volume_id: str) -> Union[str, GLCPErrorResponse]: ...

    def get_tag_keys(
        self,
        account_id: str = "00000000-0000-0000-0000-000000000001",
        regions: str = "us-east-1",
        response_code: requests.codes = requests.codes.ok,
    ) -> Union[ItemList, GLCPErrorResponse]: ...

    def get_tag_key_values(
        self,
        key: str,
        account_id: str = "00000000-0000-0000-0000-000000000001",
        regions: str = "us-east-1,us-east-2,us-west-1,us-west-2",
        response_code: requests.codes = requests.codes.ok,
    ) -> Union[TagKeyValue, GLCPErrorResponse]: ...

    def update_csp_tags(
        self,
        asset_type: AssetType,
        asset_ids: list[str],
        post_update_csp_tags: PostUpdateCSPTagsModel,
        expected_status_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, GLCPErrorResponse]: ...

    def get_subnets(
        self,
        account_id: str,
        filter: str = "",
        sort: str = "",
        response_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPSubnetListModel, GLCPErrorResponse]: ...

    def get_vpcs(
        self,
        account_id: str,
        filter: str = "",
        sort: str = "",
        response_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPVPCListModel, GLCPErrorResponse]: ...

    def get_protection_groups(
        self,
        limit: int = 1000,
        offset: int = 0,
        sort: str = "name",
        filter: str = "",
    ) -> Union[ProtectionGroupListModel, GLCPErrorResponse]: ...

    def get_protection_group_by_id(
        self,
        protection_group_id: str,
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[ProtectionGroupModel, GLCPErrorResponse]: ...

    def create_protection_group(
        self,
        post_protection_group,
        response_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, GLCPErrorResponse]: ...

    def update_protection_group(
        self,
        protection_group_id: str,
        patch_custom_protection_group: PatchCustomProtectionGroupModel,
        response_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, GLCPErrorResponse]: ...

    def update_custom_protection_group_static_members(
        self,
        protection_group_id: str,
        post_custom_protection_group_static_members: PostCustomProtectionGroupStaticMembersModel,
        response_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, GLCPErrorResponse]: ...

    def delete_protection_group(
        self,
        protection_group_id: str,
        response_status_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, GLCPErrorResponse]: ...

    def get_csp_resource_groups(
        self,
        account_id: str,
        sort: str = "name",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
        expected_error: str = None,
    ) -> Union[CSPResourceGroupListModel, GLCPErrorResponse]: ...

    def get_csp_resource_group_by_id(
        self,
        account_id: str,
        resource_group_id: UUID,
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPResourceGroupModel, GLCPErrorResponse]: ...

    def get_csp_subscriptions(
        self,
        account_id: str,
        sort: str = "name",
        expected_status_code: requests.codes = requests.codes.ok,
        expected_error: str = None,
    ) -> Union[CSPSubscriptionListModel, GLCPErrorResponse]: ...

    def get_csp_subscription_by_id(
        self,
        account_id: str,
        subscription_id: UUID,
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPSubscriptionModel, GLCPErrorResponse]: ...

    def get_csp_vpcs(
        self,
        account_id: str,
        sort: str = "name",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
        expected_error: str = None,
    ) -> Union[CSPVPCListModel, GLCPErrorResponse]: ...

    def get_csp_vpc_by_id(
        self,
        account_id: str,
        vpc_id: UUID,
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPVPCModel, GLCPErrorResponse]: ...

    def get_csp_subnets(
        self,
        account_id: str,
        sort: str = "name",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
        expected_error: str = None,
    ) -> Union[CSPSubnetListModel, GLCPErrorResponse]: ...

    def get_csp_subnet_by_id(
        self,
        account_id: str,
        subnet_id: UUID,
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPSubnetModel, GLCPErrorResponse]: ...
