import json
import logging
from enum import Enum
from json import dumps
from requests import Response, codes
from waiting import wait, TimeoutExpired
from lib.common.common import get, post, patch, delete
from lib.common.enums.app_type import AppType
from lib.dscc.backup_recovery.vmware_protection.storeonce.payload.storeonces_payload import (
    Credentials,
)
from lib.dscc.tasks.api.tasks import TaskManager
from lib.common.users.user import User
from lib.common.config.config_manager import ConfigManager
from utils.timeout_manager import TimeoutManager
from lib.common.enums.copy_pool_types import CopyPoolTypes
from lib.dscc.backup_recovery.vmware_protection.vcenter.api.hypervisor_manager import (
    HypervisorManager,
)
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.payload.copy_pool import (
    ProtectionStoresStoreonce,
)
from typing import Dict, List
from lib.dscc.backup_recovery.vmware_protection.storeonce.payload.storeonces_payload import (
    RegisterStoreOncePayload,
    PatchStoreOncePayload,
)
from lib.common.enums.aws_regions import AwsStorageLocation

logger = logging.getLogger()


class StoreonceManager:
    """
    This class contains following functions that can be performed
    from the Atlas UI for StoreOnce in Data Services Cloud Console (DSCC)

    1. Register storeonce
    2. Get list of storeonce
    3. Get storeonce informtion
    4. Patch storeonce
    5. Unregister storeonce
    """

    logger = logging.getLogger()

    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlas_api = config["ATLAS-API"]
        self.dscc = config["CLUSTER"]
        self.url = f"{self.dscc['url']}/api/{self.dscc['version']}"
        self.path = self.atlas_api["storeonces"]
        self.ope = self.atlas_api["ope"]
        self.v1beta1 = self.dscc["beta-version"]
        self.backup_recovery_url = f"{self.dscc['url']}/{self.atlas_api['backup_recovery']}/{self.v1beta1}"
        self.protection_stores = self.atlas_api["protection_stores"]
        self.backup_usage = f"app-data-management/{self.dscc['version']}/{self.atlas_api['backup_usage']}"
        self.storeonces_config = config["STOREONCE_TEST_DATA"]
        self.tasks = TaskManager(user)

    def get_storeonces(self):
        return get(self.backup_recovery_url, self.path, headers=self.user.authentication_header)

    def get_storeonce_details(self, storeonce_id):
        return get(
            self.backup_recovery_url,
            f"{self.path}/{storeonce_id}",
            headers=self.user.authentication_header,
        )

    def register_storeonce(
        self,
        network_address,
        serial_number,
        name,
        description="",
        dscc_username="",
        dscc_password="",
    ):
        payload = RegisterStoreOncePayload(
            network_address,
            serial_number,
            name,
            Credentials(dscc_username, dscc_password),
            description,
        )

        return post(
            self.backup_recovery_url,
            self.path,
            json_data=payload.to_json(),
            headers=self.user.authentication_header,
        )

    def get_copy_pools(self):
        return get(
            self.backup_recovery_url,
            self.protection_stores,
            headers=self.user.authentication_header,
        )

    def get_storeonce_by_name(self, name):
        response = self.get_storeonces()
        assert response.status_code == codes.ok, (
            f"Storeonce not fetched properly: {response.status_code}, " f"{response.text}"
        )
        try:
            item = next(filter(lambda item: item["name"] == name, response.json().get("items")))
            return item
        except StopIteration:
            print(f"Failed to find  Storeonce VM: {name}")
            return {}

    def unregister_storeonce(self, storeonce_id, force):
        if not force:
            return delete(
                self.backup_recovery_url,
                f"{self.path}/{storeonce_id}",
                headers=self.user.authentication_header,
            )
        else:
            return delete(
                self.backup_recovery_url,
                f"{self.path}/{storeonce_id}?true",
                headers=self.user.authentication_header,
            )

    def delete_protection_store(self, protection_store_id, force=False):
        return delete(
            self.backup_recovery_url,
            f"{self.protection_stores}/{protection_store_id}?force={force}",
            headers=self.user.authentication_header,
        )

    def patch_storeonce(self, network_address, description, storeonce_id):
        payload = PatchStoreOncePayload(network_address, description)

        return patch(
            self.backup_recovery_url,
            f"{self.path}/{storeonce_id}",
            json_data=payload.to_json(),
            headers=self.user.authentication_header,
        )

    def refresh_storeonce(self, storeonce_id):
        return post(
            self.backup_recovery_url,
            f"{self.path}/{storeonce_id}/refresh",
            headers=self.user.authentication_header,
        )

    @staticmethod
    def get_id(name, response):
        assert response.status_code == codes.ok, f"Status code: {response.status_code} => {response.text}"
        try:
            found_item = next(
                filter(
                    lambda item: item["name"].strip() == name.strip(),
                    response.json().get("items"),
                )
            )
            return found_item["id"]
        except StopIteration:
            print(f'StoreOnce "{name}" - not found in ATLAS')
            return None

    def get_storeonce_id(self, context):
        storeonce = self.get_storeonces()
        storeonce_id = self.get_id(context.storeonces_name, storeonce)
        return storeonce_id

    def get_secondary_storeonce_id(self, context):
        storeonce = self.get_storeonces()
        storeonce_id = self.get_id(context.second_so_name, storeonce)
        return storeonce_id

    @staticmethod
    def get_copy_pool_id(
        context,
        name,
        response,
        storeonce_id,
        pool_type: CopyPoolTypes,
        cloud_region=AwsStorageLocation.any,
    ):
        assert response.status_code == codes.ok, f"Status code: {response.status_code} => {response.text}"

        cloud_region_statement = lambda _: True
        if cloud_region != AwsStorageLocation.any and pool_type == CopyPoolTypes.cloud:
            cloud_region_statement = lambda item: item["region"] == cloud_region.value

        find_condition = (
            lambda item: item["storageSystemInfo"]["id"] == storeonce_id
            and item["protectionStoreType"] == pool_type.value
            and cloud_region_statement(item)
        )

        try:
            found_item = next(filter(find_condition, response.json().get("items")))
            if pool_type == CopyPoolTypes.cloud:
                context.aws_region = AwsStorageLocation(found_item["region"]).name
            return found_item["id"]
        except StopIteration:
            StoreonceManager.logger.info(f'No matching copy pool found for storeonce  id "{name}"')
            return None

    def get_local_cloud_copy_pools(self, context, user, cloud_region=AwsStorageLocation.any, create_cloud_pool=True):
        storeonce_id = self.get_storeonce_id(context)
        copy_pools = self.get_copy_pools()

        local_copy_pool_id = self.get_local_copy_pool(context, storeonce_id, copy_pools)
        cloud_copy_pool_id = self.get_cloud_copy_pool(
            context,
            context.storeonces_name,
            storeonce_id,
            copy_pools,
            user,
            cloud_region,
            create_cloud_pool,
        )
        logger.info("local copypool id" + str(local_copy_pool_id))
        logger.info("cloud copy pool id" + str(cloud_copy_pool_id))
        return local_copy_pool_id, cloud_copy_pool_id

    def get_local_copy_pool(self, context, storeonce_id, copy_pools):
        local_copy_pool_id = self.get_copy_pool_id(
            context,
            context.storeonces_name,
            copy_pools,
            storeonce_id,
            CopyPoolTypes.local,
        )
        logger.info("local copy pool id" + str(local_copy_pool_id))

        return local_copy_pool_id

    def get_cloud_copy_pool(
        self,
        context,
        storeonce_name,
        storeonce_id,
        copy_pools,
        user,
        cloud_region=AwsStorageLocation.any,
        create_cloud_pool=True,
    ):
        """
        Parameters:
        create_cloud_pool (bool): create cloud pool if not exists
        cloud_region (AwsStorageLocation): aws cloud region, default us-west
        """
        cloud_copy_pool_id = self.get_copy_pool_id(
            context,
            storeonce_name,
            copy_pools,
            storeonce_id,
            CopyPoolTypes.cloud,
            cloud_region,
        )

        if cloud_copy_pool_id is None and create_cloud_pool:
            cloud_copy_pool_id = self.create_cloud_copy_pool(context, storeonce_id, cloud_region)

        assert cloud_copy_pool_id is not None, "Cloud copy pool not exists"
        logger.info("cloud  copy pool id" + str(cloud_copy_pool_id))

        return cloud_copy_pool_id

    def create_cloud_copy_pool(self, context, storeonce_id, cloud_region):
        if cloud_region == AwsStorageLocation.any:
            cloud_region = AwsStorageLocation.AWS_US_EAST_1
        response_create_cloud = self.post_cloud_copy_pool(storeonce_id, cloud_region)
        assert response_create_cloud.status_code == codes.accepted, f"{response_create_cloud.content}"

        context.aws_region = cloud_region.name

        task_id = self.tasks.get_task_id_from_header(response_create_cloud)

        timeout = TimeoutManager.create_psgw_timeout
        status = self.tasks.wait_for_task(
            task_id,
            timeout,
            message=f"Create cloud protection store exceed {timeout / 60:1f} minutes - TIMEOUT",
        )
        assert status == "succeeded", f"We got wrong status: {status} for task: {self.tasks.get_task_object(task_id)}"

        # Fetch 'CopyPools' URI from associatedResource field
        task = self.tasks.get_task_object(task_id)
        associated_resource_uri = next(
            item.resource_uri for item in task.associated_resources if item.type == "PROTECTION_STORE"
        )
        return associated_resource_uri.split("/")[-1]

    def post_cloud_copy_pool(self, storeonce_id, cloud_region=AwsStorageLocation.AWS_US_EAST_1):
        payload = ProtectionStoresStoreonce(storeOnceId=storeonce_id, region=cloud_region.value).to_json()
        return post(
            self.backup_recovery_url,
            self.protection_stores,
            json_data=payload,
            headers=self.user.authentication_header,
        )

    def get_protection_stores(self):
        return get(
            self.backup_recovery_url,
            self.protection_stores,
            headers=self.user.authentication_header,
        )

    def create_protection_store(self, protection_store_payload):
        """Creates a protection store
        Args:
            protection_store_details (_type_): contains a dictionary of display name, Storeonce_id, aws region and protection store type
        Returns:
            _type_: Response object of create protection store api call
        """
        payload = json.dumps(protection_store_payload, indent=4)
        return post(
            self.backup_recovery_url,
            self.protection_stores,
            json_data=payload,
            headers=self.user.authentication_header,
        )

    def get_protection_stores_info_by_id(self, protection_store_id):
        response = get(
            self.backup_recovery_url,
            f"{self.protection_stores}/{protection_store_id}",
            headers=self.user.authentication_header,
        )
        assert (
            response.status_code == codes.ok
        ), f"failed to fetch protection store id : {response.status_code}, {response.text}"
        return response.json()

    def get_on_premises_and_cloud_protection_store(self, context, secondary_so=False):
        """Fetches the protection stores associated to current storeonce.
        Args:
            context: test_context
        Returns:
            strings: protection store ids (both cloud and on_premises)
        """
        protection_stores_response = self.get_protection_stores()
        if secondary_so:
            storeonce_id = self.get_secondary_storeonce_id(context)
        else:
            storeonce_id = self.get_storeonce_id(context)
        on_premises_store_id_list = []
        cloud_store_id_list = []
        assert (
            protection_stores_response.status_code == codes.ok
        ), f"Protection stores not fetched properly: {protection_stores_response.status_code}, {protection_stores_response.text}"
        for protection_store in protection_stores_response.json().get("items"):
            if protection_store["storageSystemInfo"]["id"] == storeonce_id:
                if protection_store["protectionStoreType"] == "ON_PREMISES":
                    on_premises_store_id_list.append(protection_store["id"])
                elif protection_store["protectionStoreType"] == "CLOUD":
                    cloud_store_id_list.append(protection_store["id"])
        return on_premises_store_id_list, cloud_store_id_list

    def reattach_protection_store(self, reattach_protection_store_payload, protection_store_id):
        payload = json.dumps(reattach_protection_store_payload, indent=4)
        return post(
            self.backup_recovery_url,
            f"{self.protection_stores}/{protection_store_id}/reattach",
            json_data=payload,
            headers=self.user.authentication_header,
        )
