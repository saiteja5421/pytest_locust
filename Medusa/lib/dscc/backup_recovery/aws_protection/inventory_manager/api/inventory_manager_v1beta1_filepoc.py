import logging
import json
from time import sleep
from typing import Union
import urllib.parse
from uuid import UUID
import requests
from requests import Response

from lib.common.common import get, post, patch, delete, get_task_id_from_header
from lib.common.config.config_manager import ConfigManager
from lib.common.enums.asset_info_types import AssetType
from lib.common.users.user import User

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import GLCPErrorResponse
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import ItemList, TagKeyValue

# Domain Model classes
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_instance_model import (
    CSPMachineInstanceModel,
    CSPMachineInstanceListModel,
)
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_resource_group_model import (
    CSPResourceGroupModel,
    CSPResourceGroupListModel,
)
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_subnet_model import (
    CSPSubnetModel,
    CSPSubnetListModel,
)
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_subscription_model import (
    CSPSubscriptionModel,
    CSPSubscriptionListModel,
)
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_vpc_model import (
    CSPVPCModel,
    CSPVPCListModel,
)
from lib.dscc.backup_recovery.aws_protection.ebs.domain_models.csp_volume_model import (
    CSPVolumeModel,
    CSPVolumeListModel,
)
from lib.dscc.backup_recovery.aws_protection.protection_groups.domain_models.protection_group_model import (
    ProtectionGroupModel,
    ProtectionGroupListModel,
)
from lib.dscc.backup_recovery.aws_protection.protection_groups.domain_models.csp_protection_group_payload_model import (
    PatchCustomProtectionGroupModel,
    PostCustomProtectionGroupModel,
    PostCustomProtectionGroupStaticMembersModel,
    PostDynamicProtectionGroupModel,
    PostUpdateCSPTagsModel,
)

# DSCC Model classes
from lib.dscc.backup_recovery.aws_protection.ec2.models.csp_machine_instance.csp_instance_v1beta1_filepoc import (
    CSPMachineInstance,
    CSPMachineInstanceList,
)
from lib.dscc.backup_recovery.aws_protection.ec2.models.csp_resource_group.csp_resource_group_v1beta1_filepoc import (
    CSPResourceGroup,
    CSPResourceGroupList,
)
from lib.dscc.backup_recovery.aws_protection.ec2.models.csp_subnet.csp_subnet_v1beta1_filepoc import (
    CSPSubnet,
    CSPSubnetList,
)
from lib.dscc.backup_recovery.aws_protection.ec2.models.csp_subscription.csp_subscription_v1beta1_filepoc import (
    CSPSubscription,
    CSPSubscriptionList,
)
from lib.dscc.backup_recovery.aws_protection.ec2.models.csp_vpc.csp_vpc_v1beta1_filepoc import (
    CSPVPC,
    CSPVPCList,
)
from lib.dscc.backup_recovery.aws_protection.ebs.models.csp_volume_v1beta1_filepoc import (
    CSPVolume,
    CSPVolumeList,
)
from lib.dscc.backup_recovery.aws_protection.protection_groups.models.protection_group_v1beta1_filepoc import (
    ProtectionGroup,
    ProtectionGroupList,
)
from lib.dscc.backup_recovery.aws_protection.protection_groups.payload.csp_protection_group_payload_v1beta1_filepoc import (
    PatchCustomProtectionGroup,
    PostCustomProtectionGroup,
    PostCustomProtectionGroupStaticMembers,
    PostDynamicProtectionGroup,
    PostUpdateCSPTags,
)

logger = logging.getLogger()


class InventoryManager:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlantia_api = config["ATLANTIA-API"]
        self.dscc = config["CLUSTER"]
        self.api_group = config["API-GROUP"]
        self.backup_recovery_url = (
            f"{self.dscc['atlantia-url']}/{self.atlantia_api['backup-recovery']}/{self.dscc['beta-version']}"
        )
        self.virtualization_url = (
            f"{self.dscc['atlantia-url']}/{self.api_group['virtualization']}/{self.dscc['beta-version']}"
        )
        self.csp_accounts = self.atlantia_api["csp-accounts"]
        self.csp_machine_instances = self.atlantia_api["csp-machine-instances"]
        self.csp_volumes = self.atlantia_api["csp-volumes"]
        self.csp_tags = self.atlantia_api["csp-tags"]
        self.csp_subnets = self.atlantia_api["csp-subnets"]
        self.csp_vpcs = self.atlantia_api["csp-vpcs"]
        self.csp_protection_groups = self.atlantia_api["protection-groups"]
        self.csp_resource_groups = self.atlantia_api["csp-resource-groups"]
        self.csp_subscriptions = self.atlantia_api["csp-subscriptions"]

    def trigger_account_inventory_sync(
        self, account_id: str, expected_status_code: requests.codes = requests.codes.accepted
    ) -> Union[str, GLCPErrorResponse]:
        response: Response = self._get_trigger_account_inventory_sync_response(account_id=account_id)
        retry_limit = 6
        # Inventory refresh time may increase depending on the number of assets in different regions.
        # Inventory retry will occur only when the expected status is ok.
        if expected_status_code == requests.codes.accepted:
            while response.status_code == requests.codes.conflict and retry_limit > 0:
                sleep(120)
                response: Response = self._get_trigger_account_inventory_sync_response(account_id=account_id)
                retry_limit -= 1
        assert response.status_code == expected_status_code, response.text
        if response.status_code == requests.codes.accepted:
            return get_task_id_from_header(response)
        else:
            return GLCPErrorResponse(**response.json())

    def _get_trigger_account_inventory_sync_response(self, account_id: str) -> Response:
        path: str = f"{self.csp_accounts}/{account_id}/refresh"
        response: Response = post(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    # region CSP Instances

    def get_csp_machine_instances(
        self,
        limit: int = 1000,
        offset: int = 0,
        sort: str = "name",
        filter: str = "",
        tag_filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
        expected_error: str = "",
    ) -> Union[CSPMachineInstanceListModel, GLCPErrorResponse]:
        response: Response = self._raw_get_csp_machine_instances(
            limit=limit, sort=sort, filter=filter, offset=offset, tag_filter=tag_filter
        )
        if expected_status_code == requests.codes.ok:
            assert response.status_code == requests.codes.ok
            csp_machine_instance_list: CSPMachineInstanceList = CSPMachineInstanceList.from_json(response.text)
            return csp_machine_instance_list.to_domain_model()
        assert response.status_code == expected_status_code, f"{response.text}"
        assert expected_error == response.json()["error"], f"{response.json()}"
        return GLCPErrorResponse(**response.json())

    def _raw_get_csp_machine_instances(
        self,
        limit: int = 1000,
        sort: str = "name",
        filter: str = "",
        offset: int = 0,
        tag_filter: str = "",
    ) -> Response:
        query_params: str = f"offset={offset}&limit={limit}&sort={sort}&filter={filter}&filter-csp-tags={tag_filter}"
        path: str = f"{self.csp_machine_instances}?{query_params}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    def get_csp_machine_instance_by_id(
        self,
        csp_machine_id: str,
        response_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPMachineInstanceModel, GLCPErrorResponse]:
        response: Response = self._raw_get_csp_machine_instance_by_id(csp_machine_id=csp_machine_id)
        assert response.status_code == response_code, response.text
        if response.status_code == requests.codes.ok:
            csp_machine_instance: CSPMachineInstance = CSPMachineInstance.from_json(response.text)
            return csp_machine_instance.to_domain_model()
        else:
            return GLCPErrorResponse(**response.json())

    def _raw_get_csp_machine_instance_by_id(self, csp_machine_id: str) -> Response:
        path: str = f"{self.csp_machine_instances}/{csp_machine_id}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    def trigger_csp_machine_instance_sync(self, csp_machine_id: str) -> Union[str, GLCPErrorResponse]:
        path: str = f"{self.csp_machine_instances}/{csp_machine_id}/refresh"
        response: Response = post(self.virtualization_url, path, headers=self.user.authentication_header)
        assert response.status_code == requests.codes.accepted
        if response.status_code == requests.codes.accepted:
            return get_task_id_from_header(response)
        else:
            return GLCPErrorResponse(**response.json())

    def get_trigger_csp_machine_instance_sync_response(self, csp_machine_id: str) -> Response:
        path: str = f"{self.csp_machine_instances}/{csp_machine_id}/refresh"
        response: Response = post(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    # endregion

    # region CSP Volumes

    def get_csp_volumes(
        self,
        limit: int = 1000,
        offset: int = 0,
        sort: str = "name",
        filter: str = "",
        tag_filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
        expected_error: str = "",
    ) -> Union[CSPVolumeListModel, GLCPErrorResponse]:
        response: Response = self._raw_get_csp_volumes(
            limit=limit, sort=sort, filter=filter, offset=offset, tag_filter=tag_filter
        )
        assert response.status_code == expected_status_code, f"{response.text}"
        if expected_status_code == requests.codes.ok:
            assert response.status_code == requests.codes.ok
            csp_volume_list: CSPVolumeList = CSPVolumeList.from_json(response.text)
            return csp_volume_list.to_domain_model()
        else:
            if expected_error:
                assert expected_error == response.json()["errorCode"], f"{response.json()}"
            return GLCPErrorResponse(**response.json())

    def _raw_get_csp_volumes(
        self,
        limit: int = 1000,
        sort: str = "name",
        filter: str = "",
        offset: int = 0,
        tag_filter: str = "",
    ) -> Response:
        query_params: str = f"offset={offset}&limit={limit}&sort={sort}&filter={filter}&filter-csp-tags={tag_filter}"
        path: str = f"{self.csp_volumes}?{query_params}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    def get_csp_volume_by_id(
        self,
        csp_volume_id: str,
        response_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPVolumeModel, GLCPErrorResponse]:
        response: Response = self._raw_get_csp_volume_by_id(csp_volume_id=csp_volume_id)
        assert response.status_code == response_code, response.text
        if response.status_code == requests.codes.ok:
            csp_volume: CSPVolume = CSPVolume.from_json(response.text)
            return csp_volume.to_domain_model()
        else:
            return GLCPErrorResponse(**response.json())

    def _raw_get_csp_volume_by_id(self, csp_volume_id: str) -> Response:
        path: str = f"{self.csp_volumes}/{csp_volume_id}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    def trigger_csp_volume_sync(self, csp_volume_id: str) -> Union[str, GLCPErrorResponse]:
        response: Response = self._raw_trigger_csp_volume_sync(csp_volume_id=csp_volume_id)
        assert response.status_code == requests.codes.accepted
        if response.status_code == requests.codes.accepted:
            return get_task_id_from_header(response)
        else:
            return GLCPErrorResponse(**response.json())

    def _raw_trigger_csp_volume_sync(self, csp_volume_id: str) -> Response:
        path: str = f"{self.csp_volumes}/{csp_volume_id}/refresh"
        response: Response = post(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    # endregion

    # region Tags

    def get_tag_keys(
        self,
        account_id: str = "00000000-0000-0000-0000-000000000001",
        regions: str = "us-east-1",
        response_code: requests.codes = requests.codes.ok,
    ) -> Union[ItemList, GLCPErrorResponse]:
        response: Response = self._raw_get_tag_keys(account_id=account_id, regions=regions)
        assert response.status_code == response_code, f"status_code={response.status_code}, text={response.text}"
        if response.status_code == requests.codes.ok:
            return ItemList(json.loads(response.text))
        return GLCPErrorResponse(**response.json())

    def _raw_get_tag_keys(self, account_id: str, regions: str) -> Response:
        path: str = f"{self.csp_accounts}/{account_id}/csp-tag-keys?csp-region={regions}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    def get_tag_key_values(
        self,
        key: str,
        account_id: str = "00000000-0000-0000-0000-000000000001",
        regions: str = "us-east-1,us-east-2,us-west-1,us-west-2",
        response_code: requests.codes = requests.codes.ok,
    ) -> Union[TagKeyValue, GLCPErrorResponse]:
        response: Response = self._raw_get_tag_key_values(key=key, account_id=account_id, regions=regions)
        assert response.status_code == response_code, f"status_code={response.status_code}, text={response.text}"
        if response.status_code == requests.codes.ok:
            return TagKeyValue(**response.json())
        return GLCPErrorResponse(**response.json())

    def _raw_get_tag_key_values(self, key: str, account_id: str, regions: str) -> Response:
        encoded_key: str = urllib.parse.quote(key)  # encoding key to parse special characters
        path: str = f"{self.csp_accounts}/{account_id}/csp-tags?filter=key%20eq%20'{encoded_key}'&regions={regions}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    def update_csp_tags(
        self,
        asset_type: AssetType,
        asset_ids: list[str],
        post_update_csp_tags: PostUpdateCSPTagsModel,
        expected_status_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, GLCPErrorResponse]:
        """
        Adds, updates, and removes tags on a set of assets of a specific type.

        Args:
            asset_type (AssetType): The type of asset represented by the asset_ids.
            asset_ids (list[str]): UUIDs of the assets for which to update tags.
            post_update_csp_tags (PostUpdateCSPTagsModel): Details of the tags to add and remove.
            expected_status_code (requests.codes): Expected response code from the API response.
        """
        if asset_type == AssetType.CSP_MACHINE_INSTANCE:
            path: str = f"{self.csp_machine_instances}/update-csp-tags?"
        elif asset_type == AssetType.CSP_VOLUME:
            path: str = f"{self.csp_volumes}/update-csp-tags?"

        # example path /update-csp-tags?id=3bdff4b5-8c4a-4db4-a272-2cae648a53df&id=f37ef01e-c054-40bc-b682-a1e453cd9cd8
        for i in range(len(asset_ids)):
            path += "id=" + asset_ids[i]
            if i != len(asset_ids) - 1:
                path += "&"

        post_update_csp_tags = PostUpdateCSPTags.from_domain_model(domain_model=post_update_csp_tags)
        response = post(
            self.virtualization_url,
            path,
            json_data=post_update_csp_tags.to_json(),
            headers=self.user.authentication_header,
        )
        assert response.status_code == expected_status_code, response.text
        if response.status_code == requests.codes.accepted:
            return get_task_id_from_header(response)
        else:
            return GLCPErrorResponse(**response.json())

    # endregion

    # region Subnets and VPCs

    def get_subnets(
        self,
        account_id: str,
        filter: str = "",
        sort: str = "",
        response_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPSubnetListModel, GLCPErrorResponse]:
        response: Response = self._raw_get_subnets(account_id=account_id, filter=filter, sort=sort)
        assert response.status_code == response_code, f"status_code={response.status_code}, text={response.text}"
        if response.status_code == requests.codes.ok:
            csp_subnet_list: CSPSubnetList = CSPSubnetList.from_json(response.text)
            return csp_subnet_list.to_domain_model()
        return GLCPErrorResponse(**response.json())

    def _raw_get_subnets(self, account_id: str, filter: str = "", sort: str = "") -> Response:
        path: str = f"{self.csp_accounts}/{account_id}/{self.csp_subnets}?filter={filter}&sort={sort}&"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    def get_vpcs(
        self,
        account_id: str,
        filter: str = "",
        sort: str = "",
        response_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPVPCListModel, GLCPErrorResponse]:
        response: Response = self._raw_get_vpcs(account_id=account_id, filter=filter, sort=sort)
        assert response.status_code == response_code, f"status_code={response.status_code}, text={response.text}"
        if response.status_code == requests.codes.ok:
            csp_vpc_list: CSPVPCList = CSPVPCList.from_json(response.text)
            return csp_vpc_list.to_domain_model()
        return GLCPErrorResponse(**response.json())

    def _raw_get_vpcs(self, account_id: str, filter: str = "", sort: str = "") -> Response:
        path: str = f"{self.csp_accounts}/{account_id}/{self.csp_vpcs}?filter={filter}&sort={sort}&"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    # endregion

    # region Protection Groups

    def get_protection_groups(
        self, limit: int = 1000, offset: int = 0, sort: str = "name", filter: str = ""
    ) -> Union[ProtectionGroupListModel, GLCPErrorResponse]:
        response: Response = self._raw_get_protection_groups(limit, offset, sort, filter)
        assert (
            response.status_code == requests.codes.ok
        ), f"GET{self.csp_protection_groups} Failed with status_code:{response.status_code} response.text:{response.text}"
        if requests.codes.ok:
            protection_group_list: ProtectionGroupList = ProtectionGroupList.from_json(response.text)
            return protection_group_list.to_domain_model()
        else:
            return GLCPErrorResponse(**response.json())

    def _raw_get_protection_groups(
        self, limit: int = 1000, offset: int = 0, sort: str = "name", filter: str = ""
    ) -> Response:
        path: str = f"{self.csp_protection_groups}?limit={limit}&offset={offset}&sort={sort}"
        # only add "filter" if it's provided
        if filter:
            path += f"&filter={filter}"
        response: Response = get(self.backup_recovery_url, path, headers=self.user.authentication_header)
        return response

    def get_protection_group_by_id(
        self, protection_group_id: str, expected_status_code: requests.codes = requests.codes.ok
    ) -> Union[ProtectionGroupModel, GLCPErrorResponse]:
        response: Response = self._raw_get_protection_group_by_id(protection_group_id)
        # validate response code is expected value
        assert response.status_code == expected_status_code
        # if OK, return response ProtectionGroupModel, else return response ErrorResponse
        if response.status_code == requests.codes.ok:
            protection_group: ProtectionGroup = ProtectionGroup.from_json(response.text)
            return protection_group.to_domain_model()
        else:
            return GLCPErrorResponse(**response.json())

    def _raw_get_protection_group_by_id(self, protection_group_id: str) -> Response:
        path: str = f"{self.csp_protection_groups}/{protection_group_id}"
        response: Response = get(self.backup_recovery_url, path, headers=self.user.authentication_header)
        return response

    def create_protection_group(
        self,
        post_protection_group: Union[PostDynamicProtectionGroupModel, PostCustomProtectionGroupModel],
        response_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, GLCPErrorResponse]:
        response = self._raw_create_protection_group(payload=post_protection_group)
        assert response.status_code == response_code, response.text
        if response.status_code == requests.codes.accepted:
            return get_task_id_from_header(response)
        else:
            return GLCPErrorResponse(**response.json())

    def _raw_create_protection_group(
        self, payload: Union[PostDynamicProtectionGroupModel, PostCustomProtectionGroupModel]
    ) -> Response:
        if isinstance(payload, PostDynamicProtectionGroupModel):
            payload = PostDynamicProtectionGroup.from_domain_model(domain_model=payload)
        else:
            payload = PostCustomProtectionGroup.from_domain_model(domain_model=payload)

        response = post(
            self.backup_recovery_url,
            self.csp_protection_groups,
            json_data=payload.to_json(),
            headers=self.user.authentication_header,
        )
        return response

    def update_protection_group(
        self,
        protection_group_id: str,
        patch_custom_protection_group: PatchCustomProtectionGroupModel,
        response_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, GLCPErrorResponse]:
        response = self._raw_update_protection_group(
            protection_group_id=protection_group_id,
            payload=patch_custom_protection_group,
        )
        assert response.status_code == response_code, response.text
        if response.status_code == requests.codes.accepted:
            return get_task_id_from_header(response)
        else:
            return GLCPErrorResponse(**response.json())

    def _raw_update_protection_group(
        self,
        protection_group_id: str,
        payload: PatchCustomProtectionGroupModel,
    ) -> Response:
        path = f"{self.csp_protection_groups}/{protection_group_id}"
        payload = PatchCustomProtectionGroup.from_domain_model(domain_model=payload)
        response = patch(
            self.backup_recovery_url,
            path,
            json_data=payload.to_json(),
            headers=self.user.authentication_header,
        )
        return response

    def update_custom_protection_group_static_members(
        self,
        protection_group_id: str,
        post_custom_protection_group_static_members: PostCustomProtectionGroupStaticMembersModel,
        response_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, GLCPErrorResponse]:
        path = f"{self.csp_protection_groups}/{protection_group_id}/update-static-members"
        payload = PostCustomProtectionGroupStaticMembers.from_domain_model(
            domain_model=post_custom_protection_group_static_members
        )
        response = post(
            self.backup_recovery_url,
            path,
            json_data=payload.to_json(),
            headers=self.user.authentication_header,
        )
        assert response.status_code == response_code, response.text
        if response.status_code == requests.codes.accepted:
            return get_task_id_from_header(response)
        else:
            return GLCPErrorResponse(**response.json())

    def delete_protection_group(
        self,
        protection_group_id: str,
        response_status_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, GLCPErrorResponse]:
        response = self._raw_delete_protection_group(protection_group_id=protection_group_id)
        assert response.status_code == response_status_code, response.content
        if response.status_code == requests.codes.accepted:
            return get_task_id_from_header(response)
        else:
            return GLCPErrorResponse(**response.json())

    def _raw_delete_protection_group(self, protection_group_id: str) -> Response:
        path = f"{self.csp_protection_groups}/{protection_group_id}"
        response = delete(self.backup_recovery_url, path, headers=self.user.authentication_header)
        return response

    # endregion Protection Groups

    # region Resource Groups

    def get_csp_resource_groups(
        self,
        account_id: str,
        sort: str = "name",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
        expected_error: str = None,
    ) -> Union[CSPResourceGroupListModel, GLCPErrorResponse]:
        """
        Returns a list of resource groups in the form of CSPResourceGroupList class object.

        Args:
            account_id (str): ID of the CSP account.
            sort (str): The field name by which to sort the result and an optional direction ("asc" or "desc").
            filter (str): A filter expression, as described in the API spec.
            expected_status_code (requests.codes): Expected status code from the API response.
            expected_error (str): Expected error from API response if any.
            example error message: "HPE_GL_ERROR_NOT_FOUND".

        Returns:
            A resource group collection in a CSPResourceGroupListModel object or a GLCPErrorResponse.
        """
        response: Response = self._raw_get_csp_resource_groups(account_id=account_id, sort=sort, filter=filter)
        assert response.status_code == expected_status_code, response.text
        if expected_status_code == requests.codes.ok:
            csp_resource_group_list: CSPResourceGroupList = CSPResourceGroupList.from_json(response.text)
            return csp_resource_group_list.to_domain_model()
        else:
            if expected_error:
                assert expected_error == response.json()["errorCode"], f"{response.json()}"
            return GLCPErrorResponse(**response.json())

    def _raw_get_csp_resource_groups(
        self,
        account_id: str,
        sort: str = "name",
        filter: str = "",
    ) -> Response:
        """
        Returns a raw response to list resource groups.

        Args:
            account_id (str): ID of the CSP account.
            sort (str): The field name by which to sort the result and an optional direction ("asc" or "desc").
            filter (str): A filter expression, as described in the API spec.

        Returns:
            A raw HTTP Response.
        """
        path: str = f"{self.csp_accounts}/{account_id}/{self.csp_resource_groups}?sort={sort}&filter={filter}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    def get_csp_resource_group_by_id(
        self,
        account_id: str,
        resource_group_id: UUID,
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPResourceGroupModel, GLCPErrorResponse]:
        """
        Returns a specific resource group by ID in the form of CSPResourceGroup class object.

        Args:
            account_id (str): ID of the CSP account.
            resource_group_id (UUID): ID of a specific resource group.
            expected_status_code (requests.codes): expected response code from the API response.

        Returns:
            A resource group in a CSPResourceGroupModel object or a GLCPErrorResponse.
        """
        response: Response = self._raw_get_csp_resource_group_by_id(
            account_id=account_id, resource_group_id=resource_group_id
        )
        assert response.status_code == expected_status_code, response.text
        if response.status_code == requests.codes.ok:
            csp_resource_group: CSPResourceGroup = CSPResourceGroup.from_json(response.text)
            return csp_resource_group.to_domain_model()
        else:
            return GLCPErrorResponse(**response.json())

    def _raw_get_csp_resource_group_by_id(self, account_id: str, resource_group_id: str) -> Response:
        """
        Returns the raw response for a specific resource group.

        Args:
            account_id (str): ID of the CSP account.
            resource_group_id (str): Resource group ID.

        Returns:
            A raw HTTP Response.
        """
        path: str = f"{self.csp_accounts}/{account_id}/{self.csp_resource_groups}/{resource_group_id}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    # endregion

    # region Subscriptions

    def get_csp_subscriptions(
        self,
        account_id: str,
        sort: str = "name",
        expected_status_code: requests.codes = requests.codes.ok,
        expected_error: str = None,
    ) -> Union[CSPSubscriptionListModel, GLCPErrorResponse]:
        """
        Returns a list of subscriptions in the form of CSPSubscriptionList class object.

        Args:
            account_id (str): ID of the CSP account.
            sort (str): The field name by which to sort the result and an optional direction ("asc" or "desc").
            expected_status_code (requests.codes): Expected status code from the API response.
            expected_error (str): Expected error from API response if any.
            example error message: "HPE_GL_ERROR_NOT_FOUND".

        Returns:
            A subscription collection in a CSPSubscriptionListModel object or a GLCPErrorResponse.
        """
        response: Response = self._raw_get_csp_subscriptions(account_id=account_id, sort=sort)
        assert response.status_code == expected_status_code, response.text
        if expected_status_code == requests.codes.ok:
            csp_subscription_list: CSPSubscriptionList = CSPSubscriptionList.from_json(response.text)
            return csp_subscription_list.to_domain_model()
        else:
            if expected_error:
                assert expected_error == response.json()["errorCode"], f"{response.json()}"
            return GLCPErrorResponse(**response.json())

    def _raw_get_csp_subscriptions(
        self,
        account_id: str,
        sort: str = "name",
    ) -> Response:
        """
        Returns a raw response to list subscriptions.

        Args:
            account_id (str): ID of the CSP account.
            sort (str): The field name by which to sort the result and an optional direction ("asc" or "desc").

        Returns:
            A raw HTTP Response.
        """
        path: str = f"{self.csp_accounts}/{account_id}/{self.csp_subscriptions}?sort={sort}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    def get_csp_subscription_by_id(
        self,
        account_id: str,
        subscription_id: UUID,
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPSubscriptionModel, GLCPErrorResponse]:
        """
        Returns a specific subscription by ID in the form of CSPSubscription class object.

        Args:
            account_id (str): ID of the CSP account.
            subscription_id (UUID): ID of a specific subscription.
            expected_status_code (requests.codes): expected response code from the API response.

        Returns:
            A subscription in a CSPSubscriptionModel object or a GLCPErrorResponse.
        """
        response: Response = self._raw_get_csp_subscription_by_id(
            account_id=account_id, subscription_id=subscription_id
        )
        assert response.status_code == expected_status_code, response.text
        if response.status_code == requests.codes.ok:
            csp_subscription: CSPSubscription = CSPSubscription.from_json(response.text)
            return csp_subscription.to_domain_model()
        else:
            return GLCPErrorResponse(**response.json())

    def _raw_get_csp_subscription_by_id(self, account_id: str, subscription_id: str) -> Response:
        """
        Returns the raw response for a specific resource group.

        Args:
            account_id (str): ID of the CSP account.
            subscription_id (str): Subscription ID.

        Returns:
            A raw HTTP Response.
        """
        path: str = f"{self.csp_accounts}/{account_id}/{self.csp_subscriptions}/{subscription_id}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    # endregion

    # region VPCs

    def get_csp_vpcs(
        self,
        account_id: str,
        sort: str = "name",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
        expected_error: str = None,
    ) -> Union[CSPVPCListModel, GLCPErrorResponse]:
        """
        Returns a list of VPCs in the form of CSPVpcList class object.

        Args:
            account_id (str): ID of the CSP account.
            sort (str): The field name by which to sort the result and an optional direction ("asc" or "desc").
            filter (str): A filter expression, as described in the API spec.
            expected_status_code (requests.codes): Expected status code from the API response.
            expected_error (str): Expected error from API response if any.

        Returns:
            A VPC collection in a CSPVPCListModel object or a GLCPErrorResponse.
        """
        response: Response = self._raw_get_csp_vpcs(account_id=account_id, sort=sort, filter=filter)
        assert response.status_code == expected_status_code, response.text
        if expected_status_code == requests.codes.ok:
            csp_vpc_list: CSPVPCList = CSPVPCList.from_json(response.text)
            return csp_vpc_list.to_domain_model()
        else:
            if expected_error:
                assert expected_error == response.json()["errorCode"], f"{response.json()}"
            return GLCPErrorResponse(**response.json())

    def _raw_get_csp_vpcs(
        self,
        account_id: str,
        sort: str = "name",
        filter: str = "",
    ) -> Response:
        """
        Returns a raw response to list VPCs.

        Args:
            account_id (str): ID of the CSP account.
            sort (str): The field name by which to sort the result and an optional direction ("asc" or "desc").
            filter (str): A filter expression, as described in the API spec.

        Returns:
            A raw HTTP Response.
        """
        path: str = f"{self.csp_accounts}/{account_id}/{self.csp_vpcs}?sort={sort}&filter={filter}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    def get_csp_vpc_by_id(
        self,
        account_id: str,
        vpc_id: UUID,
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPVPCModel, GLCPErrorResponse]:
        """
        Returns a specific VPC by ID in the form of CSPVpc class object.

        Args:
            account_id (str): ID of the CSP account.
            vpc_id (UUID): ID of a specific VPC.
            expected_status_code (requests.codes): expected response code from the API response.

        Returns:
            A VPC in a CSPVPCModel object or a GLCPErrorResponse.
        """
        response: Response = self._raw_get_csp_vpc_by_id(account_id=account_id, vpc_id=vpc_id)
        assert response.status_code == expected_status_code, response.text
        if response.status_code == requests.codes.ok:
            csp_vpc: CSPVPC = CSPVPC.from_json(response.text)
            return csp_vpc.to_domain_model()
        else:
            return GLCPErrorResponse(**response.json())

    def _raw_get_csp_vpc_by_id(self, account_id: str, vpc_id: str) -> Response:
        """
        Returns the raw response for a specific VPC.

        Args:
            account_id (str): ID of the CSP account.
            vpc_id (str): ID of a specific VPC.

        Returns:
            A raw HTTP Response.
        """
        path: str = f"{self.csp_accounts}/{account_id}/{self.csp_vpcs}/{vpc_id}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    # endregion

    # region Subnets

    def get_csp_subnets(
        self,
        account_id: str,
        sort: str = "name",
        filter: str = "",
        expected_status_code: requests.codes = requests.codes.ok,
        expected_error: str = None,
    ) -> Union[CSPSubnetListModel, GLCPErrorResponse]:
        """
        Returns a list of subnets in the form of CSPSubnetList class object.

        Args:
            account_id (str): ID of the CSP account.
            sort (str): The field name by which to sort the result and an optional direction ("asc" or "desc").
            filter (str): A filter expression, as described in the API spec.
            expected_status_code (requests.codes): Expected status code from the API response.
            expected_error (str): Expected error from API response if any.

        Returns:
            A subnet collection in a CSPSubnetListModel object or a GLCPErrorResponse.
        """
        response: Response = self._raw_get_csp_subnets(account_id=account_id, sort=sort, filter=filter)
        assert response.status_code == expected_status_code, response.text
        if expected_status_code == requests.codes.ok:
            csp_subnet_list: CSPSubnetList = CSPSubnetList.from_json(response.text)
            return csp_subnet_list.to_domain_model()
        else:
            if expected_error:
                assert expected_error == response.json()["errorCode"], f"{response.json()}"
            return GLCPErrorResponse(**response.json())

    def _raw_get_csp_subnets(
        self,
        account_id: str,
        sort: str = "name",
        filter: str = "",
    ) -> Response:
        """
        Returns a raw response to list subnets.

        Args:
            account_id (str): ID of the CSP account.
            sort (str): The field name by which to sort the result and an optional direction ("asc" or "desc").
            filter (str): A filter expression, as described in the API spec.

        Returns:
            A raw HTTP Response.
        """
        path: str = f"{self.csp_accounts}/{account_id}/{self.csp_subnets}?sort={sort}&filter={filter}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    def get_csp_subnet_by_id(
        self,
        account_id: str,
        subnet_id: UUID,
        expected_status_code: requests.codes = requests.codes.ok,
    ) -> Union[CSPSubnetModel, GLCPErrorResponse]:
        """
        Returns a specific subnet by ID in the form of CSPSubnet class object.

        Args:
            account_id (str): ID of the CSP account.
            subnet_id (UUID): ID of a specific subnet.
            expected_status_code (requests.codes): expected response code from the API response.

        Returns:
            A subnet in a CSPSubnetModel object or a GLCPErrorResponse.
        """
        response: Response = self._raw_get_csp_subnet_by_id(account_id=account_id, subnet_id=subnet_id)
        assert response.status_code == expected_status_code, response.text
        if response.status_code == requests.codes.ok:
            csp_subnet: CSPSubnet = CSPSubnet.from_json(response.text)
            return csp_subnet.to_domain_model()
        else:
            return GLCPErrorResponse(**response.json())

    def _raw_get_csp_subnet_by_id(self, account_id: str, subnet_id: str) -> Response:
        """
        Returns the raw response for a specific subnet.

        Args:
            account_id (str): ID of the CSP account.
            subnet_id (str): ID of a specific subnet.

        Returns:
            A raw HTTP Response.
        """
        path: str = f"{self.csp_accounts}/{account_id}/{self.csp_subnets}/{subnet_id}"
        response: Response = get(self.virtualization_url, path, headers=self.user.authentication_header)
        return response

    # endregion
