import json
import logging
from enum import Enum
from json import dumps
from requests import Response, codes
from waiting import wait, TimeoutExpired
from lib.common.enums.psg import HealthState, HealthStatus

from lib.common.common import get, post, patch, delete
from lib.common.enums.app_type import AppType
from lib.dscc.backup_recovery.vmware_protection.vcenter.api.hypervisor_manager import HypervisorManager
from lib.dscc.tasks.api.tasks import TaskManager
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.common.enums.copy_pool_types import CopyPoolTypes
from lib.common.users.user import User
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.payload.copy_pool import CopyPool
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.payload.patch_update_catalyst_gateway import (
    PatchUpdateCatalystGateway,
)
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.payload.patch_update_catalyst_gateway_network import (
    PatchUpdateCatalystGatewayNetwork,
)
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.payload.post_create_catalyst_gateway import (
    Network,
    VmConfig,
    Override,
    PostCreateCatalystGateway,
)
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.payload.add_storage_payload import (
    AddStoragePayload,
)
from lib.common.config.config_manager import ConfigManager
from utils.timeout_manager import TimeoutManager
from typing import Dict, List
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.payload.psgw_size_payload import (
    PsgwSizePayload,
)
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.payload.psgw_resize_payload import (
    PsgwReSizePayload,
)

logger = logging.getLogger()


class CatalystGateway:
    """
    This class contains following functions that can be performed
    from the Atlas UI for catalyst gateway in Data Services Cloud Console (DSCC)

    1. Create catalyst gateway vm
    2. Get list of catalyst gateway vms
    3. Get catalyst gateway vm informtion
    4. Update catalyst gateway vm settings
    5. Delete catalyst gateway vm
    """

    logger = logging.getLogger()

    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlas_api = config["ATLAS-API"]
        self.dscc = config["CLUSTER"]
        self.url = f"{self.dscc['url']}/api/{self.dscc['version']}"
        self.v1beta1 = self.dscc["beta-version"]
        self.backup_recovery_url = f"{self.dscc['url']}/{self.atlas_api['backup_recovery']}/{self.v1beta1}"
        self.path = self.atlas_api["protection_store_gateways"]
        self.ope = self.atlas_api["ope"]
        self.hybrid_cloud = self.atlas_api["hybrid_cloud"]
        self.protection_stores = self.atlas_api["protection_stores"]
        self.backup_usage = f"app-data-management/{self.dscc['version']}/{self.atlas_api['backup_usage']}"
        self.tasks = TaskManager(user)
        self.resize_path = self.atlas_api["resize"]
        self.psgw_sizer_path = self.atlas_api["sizer"]
        self.deploy_psgw_sizer = self.atlas_api["protection_store_gateway_sizer"]

    def get_catalyst_gateways(self):
        return get(self.backup_recovery_url, self.path, headers=self.user.authentication_header)

    def get_catalyst_gateway(self, catalyst_gateway_id):
        return get(
            self.backup_recovery_url,
            f"{self.path}/{catalyst_gateway_id}",
            headers=self.user.authentication_header,
        )

    def get_catalyst_gateway_details(self, user, catalyst_gateway):
        hypervisor = HypervisorManager(user)
        psgw_name = catalyst_gateway["name"]
        if catalyst_gateway.get("datastoresInfo"):
            datastore_id = catalyst_gateway["datastoresInfo"][0]["id"]
        response = hypervisor.get_datastore(datastore_id=datastore_id)
        vcenter_name = response.json().get("hypervisorManagerInfo")["name"]
        return psgw_name, datastore_id, vcenter_name

    def get_protection_stores(self):
        return get(self.backup_recovery_url, self.protection_stores, headers=self.user.authentication_header)

    def get_protection_stores_info_by_id(self, protection_store_id, ignore_assert=True):
        response = get(
            self.backup_recovery_url,
            f"{self.protection_stores}/{protection_store_id}",
            headers=self.user.authentication_header,
        )
        if ignore_assert:
            assert (
                response.status_code == codes.ok
            ), f"failed to fetch protection store id : {response.status_code}, {response.text}"
        return response.json()

    def get_catalyst_gateway_by_name(self, name):
        response = self.get_catalyst_gateways()
        assert response.status_code == codes.ok, (
            f"Catalyst gateways not fetched properly: {response.status_code}, " f"{response.text}"
        )
        try:
            item = next(filter(lambda item: item["name"] == name, response.json().get("items")))
            return item
        except StopIteration:
            print(f"Failed to find Protection Store Gateway VM: {name}")
            return {}

    def get_list_of_all_available_psg_ips(self):
        """This method fetches IPs of all PSGs (of all states) in DSCC

        Returns:
            List: Returns list of IPs of all PSGs (of all states) in DSCC
        """
        response = self.get_catalyst_gateways()
        assert response.status_code == codes.ok, (
            f"Catalyst gateways not fetched properly: {response.status_code}, " f"{response.text}"
        )
        list_of_available_psg_ips = []
        for item in response.json().get("items"):
            # if any one psg stuck at deploying state it doesn't have nics data.
            if item.get("network", {}).get("nics"):
                list_of_available_psg_ips.append(item["network"]["nics"][0]["networkAddress"])
        return list_of_available_psg_ips

    def get_catalyst_gateway_health_state(self, name):
        item = self.get_catalyst_gateway_by_name(name)
        return item.get("health", {}).get("state")

    def get_catalyst_gateway_health_status(self, name):
        item = self.get_catalyst_gateway_by_name(name)
        return item.get("health", {}).get("status")

    def get_catalyst_gateway_connected(self, context):
        response = self.get_catalyst_gateways()
        CatalystGateway.logger.info(f"Response of get catalyst gateways: {response.json()}")
        assert response.status_code == codes.ok, (
            f"Catalyst gateways not fetched properly: {response.status_code}, " f"{response.text}"
        )

        try:
            items = filter(
                lambda item: item["name"] == context.psgw_name,
                response.json().get("items"),
            )

            # items = filter(
            #     lambda item: item["health"]["status"] == "CG_HEALTH_STATUS_CONNECTED"
            #     or item["state"] in (HealthState.OK.value, HealthState.WARNING.value, HealthState.DEPLOYING.value),
            #     response.json().get("items"),
            # )

            vcenters_name_list = [vcenter["ip"] for vcenter in context.vcenters]

            psgw_name = None
            datastore_id = None
            vcenter_name = None

            for item in items:
                (
                    psgw_name,
                    datastore_id,
                    vcenter_name,
                ) = self.get_catalyst_gateway_details(context.user, item)
                if (
                    vcenter_name in vcenters_name_list and vcenter_name not in context.excluded_vcenters
                ) and psgw_name == context.psgw_name:
                    break
                psgw_name = datastore_id = vcenter_name = None

            CatalystGateway.logger.info(
                f"Selected PSGW info: {psgw_name}, datastore id: {datastore_id}, vcenter: {vcenter_name}"
            )
            return psgw_name, datastore_id, vcenter_name

        except StopIteration:
            CatalystGateway.logger.info("Failed to find any existing Protection Store Gateway VM")
            return None, None, None

    def check_copy_pool_status(self, task_id, user):
        task = self.tasks.get_task_object(task_id)
        associated_resource_uri = next(
            item.get("resourceUri") for item in task.associated_resources if item.get("type") == "PROTECTION_STORE"
        )
        copy_pool_id = associated_resource_uri.split("/")[-1]

        def _return_condition():
            copy_pools = self.get_protection_stores().json().get("items")
            item = next(filter(lambda item: item["id"] == copy_pool_id, copy_pools))
            return (
                item["state"] == "Ok"
                and item["status"] == "Ok"
                and int(item["sizeOnDiskInBytes"]) > 0
                and int(item["userDataStoredInBytes"]) == 0
                and int(item["maxCapacityInBytes"]) > 102400
            )

        try:
            wait(
                _return_condition,
                timeout_seconds=TimeoutManager.standard_task_timeout,
                sleep_seconds=20,
            )
        except TimeoutExpired:
            raise AssertionError("Created copy pool health state and status are not in good condition")

    @staticmethod
    def get_copy_pool_id(
        context,
        name,
        response,
        catalyst_gateway_id,
        pool_type: CopyPoolTypes,
        cloud_region=AwsStorageLocation.any,
    ):
        assert response.status_code == codes.ok, f"Status code: {response.status_code} => {response.text}"

        cloud_region_statement = lambda _: True
        if cloud_region != AwsStorageLocation.any and pool_type == CopyPoolTypes.cloud:
            cloud_region_statement = lambda item: item["location"] == cloud_region.value

        find_condition = (
            lambda item: item["storageSystemInfo"]["id"] == catalyst_gateway_id
            and item["protectionStoreType"] == pool_type.value
            and cloud_region_statement(item)
        )

        try:
            found_item = next(filter(find_condition, response.json().get("items")))
            if pool_type == CopyPoolTypes.cloud:
                context.aws_region = AwsStorageLocation(found_item["storageLocationInfo"]["id"]).value
            return found_item["id"]
        except StopIteration:
            CatalystGateway.logger.info(f'No matching copy pool found for catalyst gateway id "{name}"')
            return None

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
            print(f'PSGW VM "{name}" - not found in {response}')
            return None

    def get_catalyst_gateway_id(self, context):
        catalyst_gateways = self.get_catalyst_gateways()
        catalyst_gateway_id = self.get_id(context.psgw_name, catalyst_gateways)
        return catalyst_gateway_id

    def get_local_cloud_copy_pools(self, context, user, cloud_region=AwsStorageLocation.any, create_cloud_pool=True):
        catalyst_gateway_id = self.get_catalyst_gateway_id(context)
        copy_pools = self.get_protection_stores()

        local_copy_pool_id = self.get_local_copy_pool(context, catalyst_gateway_id, copy_pools)
        cloud_copy_pool_id = self.get_cloud_copy_pool(
            context,
            context.psgw_name,
            catalyst_gateway_id,
            copy_pools,
            user,
            cloud_region,
            create_cloud_pool,
        )

        return local_copy_pool_id, cloud_copy_pool_id

    def get_local_copy_pool(self, context, catalyst_gateway_id, copy_pools):
        local_copy_pool_id = self.get_copy_pool_id(
            context, context.psgw_name, copy_pools, catalyst_gateway_id, CopyPoolTypes.local
        )

        return local_copy_pool_id

    def get_cloud_copy_pool(
        self,
        context,
        psgw_name,
        catalyst_gateway_id,
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
            psgw_name,
            copy_pools,
            catalyst_gateway_id,
            CopyPoolTypes.cloud,
            cloud_region,
        )

        if cloud_copy_pool_id is None and create_cloud_pool:
            cloud_copy_pool_id = self.create_cloud_copy_pool(context, catalyst_gateway_id, cloud_region)

        assert cloud_copy_pool_id is not None, "Cloud copy pool not exists"
        return cloud_copy_pool_id

    def get_cloud_copy_pool_recover(
        self,
        context,
        psgw_name,
        catalyst_gateway_id,
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
            psgw_name,
            copy_pools,
            catalyst_gateway_id,
            CopyPoolTypes.cloud,
            cloud_region,
        )
        cloud_copy_pool_task_id = ""
        if cloud_copy_pool_id is None and create_cloud_pool:
            cloud_copy_pool_id, cloud_copy_pool_task_id = self.create_cloud_copy_pool_recover(
                context, catalyst_gateway_id, cloud_region
            )

        assert cloud_copy_pool_id is not None, "Cloud copy pool not exists"
        logger.info(f"Getting cloud copy pool task id during recover {cloud_copy_pool_task_id}")
        return cloud_copy_pool_id, cloud_copy_pool_task_id

    def create_catalyst_gateway_vm(
        self,
        name,
        hypervisor_id,
        datastore_info,
        host_id,
        hypervisor_cluster_id,
        content_lib_datastore_id,
        hypervisor_folder_id,
        resources_pools_id,
        network_name,
        network_address,
        subnet_mask,
        gateway,
        network_type,
        max_cld_dly_prtctd_data=1.0,
        max_cld_rtn_days=1,
        max_onprem_dly_prtctd_data=1.0,
        max_onprem_rtn_days=1,
        override_cpu=0,
        override_ram_gib=0,
        override_storage_tib=0,
        deploy_ova_on_content_lib_ds=False,
        deploy_on_folder=False,
        deploy_with_cluster_id=False,
        deploy_with_resource_pools=False,
    ):
        network = Network(network_name, network_address, subnet_mask, gateway, network_type)
        override = Override(override_cpu, override_ram_gib, override_storage_tib)
        vm_config = VmConfig(
            host_id,
            hypervisor_cluster_id,
            content_lib_datastore_id,
            hypervisor_folder_id,
            resources_pools_id,
            max_cld_dly_prtctd_data,
            max_cld_rtn_days,
            max_onprem_dly_prtctd_data,
            max_onprem_rtn_days,
            network,
            override,
            datastore_info,
        )
        payload = PostCreateCatalystGateway(name, hypervisor_id, vm_config).to_dict()
        if deploy_ova_on_content_lib_ds == False:
            del payload["vmConfig"]["contentLibraryId"]

        if deploy_on_folder == False:
            del payload["vmConfig"]["folderId"]

        if deploy_with_cluster_id == True and deploy_with_resource_pools == False:
            del payload["vmConfig"]["hostId"]
            del payload["vmConfig"]["resourcePoolId"]
        elif deploy_with_resource_pools == True and deploy_with_cluster_id == False:
            del payload["vmConfig"]["clusterId"]
            del payload["vmConfig"]["hostId"]
        elif deploy_with_resource_pools == False and deploy_with_cluster_id == False:
            del payload["vmConfig"]["clusterId"]
            del payload["vmConfig"]["resourcePoolId"]

        return post(
            self.backup_recovery_url,
            self.path,
            json_data=json.dumps(payload, indent=4),
            headers=self.user.authentication_header,
        )

    def update_catalyst_gateway_vm(
        self,
        catalyst_id,
        datastore_id=None,
        method_date_time_set=None,
        timezone=None,
        utc_date_time=None,
        dns_network_address=None,
        ntp_network_address=None,
        username=None,
        password=None,
        network_address=None,
        port=None,
    ):
        payload = PatchUpdateCatalystGateway(
            datastore_id,
            method_date_time_set,
            timezone,
            utc_date_time,
            dns_network_address,
            ntp_network_address,
            username,
            password,
            network_address,
            port,
        )
        return patch(
            self.backup_recovery_url,
            f"{self.path}/{catalyst_id}",
            json_data=payload.update(),
            headers=self.user.authentication_header,
        )

    def update_catalyst_gateway_vm_network(
        self,
        catalyst_id,
        nic_id=None,
        gateway=None,
        name=None,
        network_address=None,
        network_type=None,
        subnet_mask=None,
    ):
        payload = PatchUpdateCatalystGatewayNetwork(nic_id, gateway, network_address, network_type, subnet_mask)
        return patch(
            self.backup_recovery_url,
            f"{self.path}/catalyst_id/updateNic",
            json_data=payload.update(),
            headers=self.user.authentication_header,
        )

    def shutdown_catalyst_gateway_vm(self, catalyst_gateway_id):
        return post(
            self.backup_recovery_url,
            f"{self.path}/{catalyst_gateway_id}/shutdown-guest-os",
            headers=self.user.authentication_header,
        )

    def poweron_catalyst_gateway_vm(self, catalyst_gateway_id):
        return post(
            self.backup_recovery_url,
            f"{self.path}/{catalyst_gateway_id}/power-on",
            headers=self.user.authentication_header,
        )

    def restart_catalyst_gateway_vm(self, catalyst_gateway_id):
        return post(
            self.backup_recovery_url,
            f"{self.path}/{catalyst_gateway_id}/restart-guest-os",
            headers=self.user.authentication_header,
        )

    def set_catalyst_gateway_vm_remote_support(self, catalyst_gateway_id, enabled=True):
        payload = {"enabled": enabled}
        return post(
            self.backup_recovery_url,
            f"{self.path}/{catalyst_gateway_id}/set-remote-support",
            json_data=dumps(payload),
            headers=self.user.authentication_header,
        )

    def generate_catalyst_gateway_vm_support_bundle(self, catalyst_gateway_id, desc="", slim=False):
        payload = {"description": desc, "slim": slim}
        return post(
            self.backup_recovery_url,
            f"{self.path}/{catalyst_gateway_id}/generate-support-bundle",
            json_data=dumps(payload),
            headers=self.user.authentication_header,
        )

    def post_catalyst_gateway_vm_console_user(self, catalyst_gateway_id):
        return post(
            self.backup_recovery_url,
            f"{self.path}/{catalyst_gateway_id}/consoleUser",
            headers=self.user.authentication_header,
        )

    def delete_catalyst_gateway_vm(self, catalyst_gateway_id):
        return delete(
            self.backup_recovery_url,
            f"{self.path}/{catalyst_gateway_id}",
            headers=self.user.authentication_header,
        )

    def update_dns_address(self, dns_address, catalyst_gateway_id):
        payload = PatchUpdateCatalystGateway(dns_networkAddress=dns_address)
        return patch(
            self.backup_recovery_url,
            f"{self.path}/{catalyst_gateway_id}",
            json_data=payload.update(),
            headers=self.user.authentication_header,
        )

    def update_proxy_address(self, proxy_address, port, catalyst_gateway_id):
        payload = PatchUpdateCatalystGateway(proxy_address=proxy_address, port=port)
        return patch(
            self.backup_recovery_url,
            f"{self.path}/{catalyst_gateway_id}",
            json_data=payload.update(),
            headers=self.user.authentication_header,
        )

    def update_ntp_address(self, ntp_address, catalyst_gateway_id):
        ntp = {
            "ntp": [{"networkAddress": ntp_address}],
            "dateTime": {"methodDateTimeSet": "NTP"},
        }
        return patch(
            self.backup_recovery_url,
            f"{self.path}/{catalyst_gateway_id}",
            json_data=dumps(ntp),
            headers=self.user.authentication_header,
        )

    def update_network_interface(self, catalyst_gateway_id, nic_details):
        return post(
            self.backup_recovery_url,
            f"{self.path}/{catalyst_gateway_id}/updateNic",
            json_data=nic_details.to_json(),
            headers=self.user.authentication_header,
        )

    def delete_network_interface(self, catalyst_gateway_id, nic_details):
        return post(
            self.backup_recovery_url,
            f"{self.path}/{catalyst_gateway_id}/deleteNic",
            json_data=nic_details.to_json(),
            headers=self.user.authentication_header,
        )

    def get_network_interface_id_by_network_address(self, psgw_id, network_address):
        response = self.get_catalyst_gateway(psgw_id)
        try:
            nic = next(
                filter(
                    lambda item: item["networkAddress"] == network_address,
                    response.json().get("network").get("nics"),
                )
            )
            return nic["id"]
        except StopIteration:
            print(f"Failed to find network ID for the address '{network_address}'")
            return

    def create_network_interface(self, catalyst_gateway_id, nic_details):
        return post(
            self.backup_recovery_url,
            f"{self.path}/{catalyst_gateway_id}/createNic",
            json_data=nic_details.to_json(),
            headers=self.user.authentication_header,
        )

    def post_copypools(self, task_id, region: str = None):
        catalyst_gateway_id: str
        response = self.tasks.get_task(task_id)
        assert response.status_code == codes.ok, f"Task does not exixst: {response.status_code}, {response.text}"
        content = response.json()
        if "sourceResource" in content and "resourceUri" in content["sourceResource"]:
            catalyst_gateway_id = content["sourceResource"]["resourceUri"].split("/")[-1]
        payload = {"catalystGatewayId": catalyst_gateway_id}
        if region:
            payload.update({"region": region})
        return post(
            self.backup_recovery_url,
            self.protection_stores,
            json_data=dumps(payload),
            headers=self.user.authentication_header,
        )

    def create_cloud_copy_pool(self, context, catalyst_gateway_id, cloud_region):
        if cloud_region == AwsStorageLocation.any:
            cloud_region = AwsStorageLocation.AWS_US_EAST_1
        response_create_cloud = self.post_cloud_copy_pool(catalyst_gateway_id, cloud_region)
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

    def create_cloud_copy_pool_recover(self, context, catalyst_gateway_id, cloud_region):
        if cloud_region == AwsStorageLocation.any:
            cloud_region = AwsStorageLocation.AWS_US_EAST_1
        response_create_cloud = self.post_cloud_copy_pool(catalyst_gateway_id, cloud_region)
        context.aws_region = cloud_region.name
        cloud_store_copy_pool_task_id = self.tasks.get_task_id_from_header(response_create_cloud)
        task = self.tasks.get_task_object(cloud_store_copy_pool_task_id)
        logger.info(
            f"requested to create cloud copy pool in {cloud_region} region for psg: {catalyst_gateway_id} and task id is: {task} "
        )
        associated_resource_uri = next(
            item.resource_uri for item in task.associated_resources if item.type == "PROTECTION_STORE"
        )
        logger.info(f"Getting associated resource uri in the  task : {associated_resource_uri}")
        logger.info(f"cloud store task id {cloud_store_copy_pool_task_id} for this region{cloud_region}")
        return associated_resource_uri.split("/")[-1], cloud_store_copy_pool_task_id

    def post_cloud_copy_pool(self, protection_store_gateway_id, cloud_region=AwsStorageLocation.AWS_US_EAST_1):
        payload = CopyPool(protectionStoreGatewayId=protection_store_gateway_id, region=cloud_region.value).to_json()
        return post(
            self.backup_recovery_url,
            self.protection_stores,
            json_data=payload,
            headers=self.user.authentication_header,
        )

    def get_backup_capacity_usage_summary(self, backup_type: Enum, app_type: Enum = AppType.vmware):
        return get(
            self.dscc["url"],
            self.backup_usage + f"?appType={app_type.value}&backupType={backup_type.value}",
            headers=self.user.authentication_header,
        )

    def add_storage(
        self,
        psgw_name: str,
        update_psg_size: int,
        psgw_id: str,
        additional_ds_name: str = None,
        additional_ds_required: bool = False,
    ) -> post:
        """Resize catalyst gateway storage cpacity

        Args:
            psgw_name (str): name of the psgw
            update_psg_size (int): additional psgw size to resize psgw
            psgw_id (str): id of psgw to resize
            additional_ds_name (str, optional): datastore name, to fetch additional datastores. Defaults to None.
            additional_ds_required (bool, optional): additional datastore required to resize?. Defaults to False.

        Returns:
            post: task id of a resize operation
        """
        psgw_datastore_info = self.get_catalyst_gateway_datastores(psgw_name)
        datastore_info = []
        if additional_ds_required:
            additional_datastore_info = self.get_additional_datastores(additional_ds_name)
            datastore_ids = additional_datastore_info + psgw_datastore_info
            # eliminate duplicate datastore ids from the list
            datastore_info = [
                dict(datastore_id_list)
                for datastore_id_list in {tuple(datastore_id.items()) for datastore_id in datastore_ids}
            ]
        else:
            datastore_info = psgw_datastore_info
        psg_size = self.get_catalyst_gateway_local_store_size(psgw_name)
        total_psg_size = psg_size + int(update_psg_size)
        CatalystGateway.logger.info(f"Total PSGW storage expansion size is: {total_psg_size}")
        resize_path = f"{self.path}/{psgw_id}/{self.resize_path}"
        payload = AddStoragePayload(datastore_info, total_psg_size)
        return post(
            self.backup_recovery_url,
            resize_path,
            json_data=payload.create(),
            headers=self.user.authentication_header,
        )

    def get_catalyst_gateway_datastores(self, psgw_name: str) -> List:
        """Get the catalyst gateway datastore/s id/s

        Args:
            psgw_name (string): psg gateway name

        Returns:
            list: list of datastore/s id/s
        """
        catalyst_gateway = self.get_catalyst_gateway_by_name(psgw_name)
        CatalystGateway.logger.info(f"Catalyst VM: {psgw_name} response: {catalyst_gateway}")
        datastore_list = [ds_info.get("id") for ds_info in catalyst_gateway.get("datastoresInfo")]
        CatalystGateway.logger.info(f"Existing Catalyst VM: {psgw_name} datastore list: {datastore_list}")
        return datastore_list

    def get_catalyst_gateway_local_store_size(self, psgw_name: str) -> int:
        """Get the size of catalyst gateway local store

        Args:
            psgw_name (string): psg gateway name

        Returns:
            int: size of catalyst gateway local store
        """
        catalyst_gateway = self.get_catalyst_gateway_by_name(psgw_name)
        catalyst_gateway_ds_info = catalyst_gateway["datastoresInfo"]
        CatalystGateway.logger.info(f"PSGW Datastores information: {catalyst_gateway_ds_info}")
        psg_size = 0
        for datastore in catalyst_gateway_ds_info:
            disk_size = datastore["totalProvisionedDiskInTiB"]
            psg_size = psg_size + disk_size
        CatalystGateway.logger.info(f"Existing PSGW size: {psg_size}")
        return psg_size

    def get_additional_datastores(self, additional_ds_name: str) -> List:
        """Get the additional datastore/s id to resize the catalyst gateway

        Args:
            additional_ds_name (string): datastore name

        Returns:
            list: list of datastore/s id/s
        """
        hypervisor = HypervisorManager(self.user)
        response = hypervisor.get_datastores()
        assert response.status_code == codes.ok, (
            f"Unable to fetch datastores: {response.status_code}, " f"{response.text}"
        )
        datastores = response.json().get("items")
        datastore_list = []
        for datastore in datastores:
            if additional_ds_name in datastore["name"]:
                datastore_list.append(datastore["id"])
        CatalystGateway.logger.info(f"Additional datastore list is: {datastore_list}")
        return datastore_list

    def recover_catalyst_gateway_vm(
        self,
        catalyst_gateway_id,
        hypervisor_id,
        datastore_info,
        host_id,
        hypervisor_cluster_id,
        content_lib_datastore_id,
        hypervisor_folder_id,
        resources_pools_id,
        network_name,
        network_address,
        subnet_mask,
        gateway,
        network_type,
        recover_psgw_name="recover_psgw",
        max_cld_dly_prtctd_data=1.0,
        max_cld_rtn_days=1,
        max_onprem_dly_prtctd_data=1.0,
        max_onprem_rtn_days=1,
        override_cpu=0,
        override_ram_gib=0,
        override_storage_tib=0,
        deploy_ova_on_content_lib_ds=False,
        deploy_on_folder=False,
        deploy_with_cluster_id=False,
        deploy_with_resource_pools=False,
    ):
        """Performs PSG Recover operation"""
        network = Network(network_name, network_address, subnet_mask, gateway, network_type)
        override = Override(override_cpu, override_ram_gib, override_storage_tib)
        vm_config = VmConfig(
            host_id,
            hypervisor_cluster_id,
            content_lib_datastore_id,
            hypervisor_folder_id,
            resources_pools_id,
            max_cld_dly_prtctd_data,
            max_cld_rtn_days,
            max_onprem_dly_prtctd_data,
            max_onprem_rtn_days,
            network,
            override,
            datastore_info,
        )
        payload = PostCreateCatalystGateway(recover_psgw_name, hypervisor_id, vm_config).to_dict()

        if deploy_ova_on_content_lib_ds == False:
            del payload["vmConfig"]["contentLibraryId"]

        if deploy_on_folder == False:
            del payload["vmConfig"]["folderId"]

        if deploy_with_cluster_id == True and deploy_with_resource_pools == False:
            del payload["vmConfig"]["hostId"]
            del payload["vmConfig"]["resourcePoolId"]
        elif deploy_with_resource_pools == True and deploy_with_cluster_id == False:
            del payload["vmConfig"]["clusterId"]
            del payload["vmConfig"]["hostId"]
        elif deploy_with_resource_pools == False and deploy_with_cluster_id == False:
            del payload["vmConfig"]["clusterId"]
            del payload["vmConfig"]["resourcePoolId"]
        return post(
            self.backup_recovery_url,
            f"{self.path}/{catalyst_gateway_id}/recover",
            json_data=json.dumps(payload, indent=4),
            headers=self.user.authentication_header,
        )

    def psgw_required_sizer_fields_to_resize(
        self,
        psgw_id: str,
        max_cld_dly_prtctd_data: float = 15.0,
        max_cld_rtn_days: int = 365,
        max_onprem_dly_prtctd_data: float = 50.0,
        max_onprem_rtn_days: int = 30,
    ) -> Response:
        """This API returns the resource requirements that would be needed for a Protection Store Gateway.

        Args:
            psgw_id (str): catalyst gateway id
            max_cld_dly_prtctd_data (float, optional): The maximum total size of the assets that is expected to be protected each day in the Cloud Protection Stores. Defaults to 15 TiB
            max_cld_rtn_days (int, optional): The maximum retention period for cloud backups in days. Defaults to 365 days.
            max_onprem_dly_prtctd_data (float, optional): The maximum total size of the assets that is expected to be protected each day in the On-Prem Protection Store. Defaults to 50.0 TiB.
            max_onprem_rtn_days (int, optional): The maximum retention period for local backups in days. Defaults to 30 days.

        Returns:
            Response: Required sizer fields to resize a Protection Store Gateway
        """

        psgw_sizer_api_path = f"{self.path}/{psgw_id}/{self.psgw_sizer_path}"
        payload = PsgwSizePayload(
            max_cld_dly_prtctd_data, max_cld_rtn_days, max_onprem_dly_prtctd_data, max_onprem_rtn_days
        ).to_json()
        return post(
            self.backup_recovery_url,
            psgw_sizer_api_path,
            json_data=payload,
            headers=self.user.authentication_header,
        )

    def required_size_fields_to_create_psgw(
        self,
        max_cld_dly_prtctd_data: float = 1.0,
        max_cld_rtn_days: int = 1,
        max_onprem_dly_prtctd_data: float = 1.0,
        max_onprem_rtn_days: int = 1,
    ) -> Response:
        """This API returns the resource requirements that would be needed for a Protection Store Gateway.

        Args:
            max_cld_dly_prtctd_data (float, optional): The maximum total size of the assets that is expected to be protected each day in the Cloud Protection Stores. Defaults to 1.0 TiB
            max_cld_rtn_days (int, optional): The maximum retention period for cloud backups in days. Defaults to 1 day.
            max_onprem_dly_prtctd_data (float, optional): The maximum total size of the assets that is expected to be protected each day in the On-Prem Protection Store. Defaults to 1.0 TiB.
            max_onprem_rtn_days (int, optional): The maximum retention period for local backups in days. Defaults to 1 day.

        Returns:
            Response: Required sizer fields to resize a Protection Store Gateway
        """
        payload = PsgwSizePayload(
            max_cld_dly_prtctd_data,
            max_cld_rtn_days,
            max_onprem_dly_prtctd_data,
            max_onprem_rtn_days,
        ).to_json()
        return post(
            self.backup_recovery_url,
            self.deploy_psgw_sizer,
            json_data=payload,
            headers=self.user.authentication_header,
        )

    def resize_existing_psgw(
        self,
        psgw_id: str,
        datastore_info: list,
        max_cld_dly_prtctd_data: float = 15.0,
        max_cld_rtn_days: int = 365,
        max_onprem_dly_prtctd_data: float = 50.0,
        max_onprem_rtn_days: int = 30,
        override_cpu=0,
        override_ram_gib=0,
        override_storage_tib=0,
    ) -> Response:
        """Reconfigure the CPU, memory and storage requirements of the Catalyst Gateway.

        Args:
            psgw_id (str): protection store gateway ID
            datastore_info (list): list of datastores
            max_cld_dly_prtctd_data (float, optional): The maximum total size of the assets that is expected to be protected each day in the Cloud Protection Stores. Defaults to 15 TiB
            max_cld_rtn_days (int, optional): The maximum retention period for cloud backups in days. Defaults to 365 days.
            max_onprem_dly_prtctd_data (float, optional): The maximum total size of the assets that is expected to be protected each day in the On-Prem Protection Store. Defaults to 50.0 TiB.
            max_onprem_rtn_days (int, optional): The maximum retention period for local backups in days. Defaults to 30 days.

        Returns:
            Response: Response object of a resize operation
        """
        override = Override(override_cpu, override_ram_gib, override_storage_tib)
        resize_path = f"{self.path}/{psgw_id}/{self.resize_path}"
        payload = PsgwReSizePayload(
            max_cld_dly_prtctd_data,
            max_cld_rtn_days,
            max_onprem_dly_prtctd_data,
            max_onprem_rtn_days,
            override,
            datastore_info,
        ).to_json()
        return post(
            self.backup_recovery_url,
            resize_path,
            json_data=payload,
            headers=self.user.authentication_header,
        )

    def psgw_total_disk_size_tib(self, psgw_name: str) -> float:
        """Protection store gateway total size in TiB

        Args:
            psgw_name (str): Name of the protection store gateway

        Returns:
            float: Returns protection store gateway total size in TiB
        """
        psgw_item = self.get_catalyst_gateway_by_name(psgw_name)
        datastores_info = psgw_item["datastoresInfo"]
        psgw_size = 0
        for datastore in datastores_info:
            datastore_size = datastore["totalProvisionedDiskInTiB"]
            psgw_size = psgw_size + datastore_size
        return psgw_size

    def psgw_compute_info(self, user: User, psgw_name: str) -> dict:
        """Compute info such as CPU and RAM of a protection store gateway

        Args:
            user (User): context user
            psgw_name (str): protection store gateway name

        Returns:
            dict: returns dictionary, which contains CPU and RAM
        """
        hypervisor_manager = HypervisorManager(user)
        response = hypervisor_manager.get_vms()
        psgw_vm = next(
            filter(
                lambda item: item["name"] == psgw_name and item["state"] == "OK",
                response.json().get("items") if response.json().get("items") else [],
            )
        )
        logger.info(f"PSGW Name : {psgw_vm['name']}")
        compute_info = psgw_vm["computeInfo"]
        return compute_info

    def get_psgw_network_interfaces(self, psg_name):
        psgw = self.get_catalyst_gateway_by_name(psg_name)
        nics = psgw["network"]["nics"]
        return nics

    def create_protection_store(self, protection_store_payload):
        """Creates a protection store
        Args:
            protection_store_details (_type_): contains a dictionary of display name, psgw_id, aws region and protection store type
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

    def get_on_premises_and_cloud_protection_store(self, context):
        """Fetches the protection stores associated to current psg.

        Args:
            context: test_context

        Returns:
            strings: protection store ids (both cloud and on_premises)
        """
        protection_stores_response = self.get_protection_stores()
        psgw_id = self.get_catalyst_gateway_id(context)
        on_premises_store_id_list = []
        cloud_store_id_list = []
        assert (
            protection_stores_response.status_code == codes.ok
        ), f"Protection stores not fetched properly: {protection_stores_response.status_code}, {protection_stores_response.text}"
        for protection_store in protection_stores_response.json().get("items"):
            if protection_store["storageSystemInfo"]["id"] == psgw_id:
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

    def delete_protection_store(self, protection_store_id, force=False):
        return delete(
            self.backup_recovery_url,
            f"{self.protection_stores}/{protection_store_id}?force={force}",
            headers=self.user.authentication_header,
        )

    def update_protection_store(self, protection_store_id):
        # Fetch display name from protection store id
        protection_store = self.get_protection_stores_info_by_id(protection_store_id)
        display_name = protection_store["displayName"]
        update_protection_store_payload = {
            "displayName": display_name,
        }
        logger.info(f"Update protectio store payload: {update_protection_store_payload}")
        payload = json.dumps(update_protection_store_payload, indent=4)
        return patch(
            self.backup_recovery_url,
            f"{self.protection_stores}/{protection_store_id}",
            json_data=payload,
            headers=self.user.authentication_header,
        )

    def validate_psg_connectivity_to_target_address(self, psgw_id, target_address, type):
        """This method validates psg connectivity to target address.

        Args:
            psgw_id (string): PSGW id.
            target_address (string): Address to which psg connectivity needs to be checked.
            type (string): Connectivity check through ping or traceroute.

        Returns:
            _type_: response of POST api call
        """
        psg_connectivity_payload = {
            "address": target_address,
        }
        logger.info(f"PSGW connectivity payload : {psg_connectivity_payload}")
        payload = json.dumps(psg_connectivity_payload, indent=4)
        return post(
            self.backup_recovery_url,
            f"{self.path}/{psgw_id}/{type}",
            json_data=json.dumps(psg_connectivity_payload, indent=4),
            headers=self.user.authentication_header,
        )
