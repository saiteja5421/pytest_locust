import logging
import os
import string
import random

from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_fixed

from lib.common.config.config_manager import ConfigManager
import ast
from requests import codes
from lib.dscc.backup_recovery.vmware_protection.minio_client.minio_client_bucket import MinioBuckets
from lib.platform.storeonce.storeonce import StoreOnce

from lib.dscc.backup_recovery.vmware_protection.data_orchestrator.api.ope import OPE
from lib.dscc.backup_recovery.vmware_protection.storeonce.api.storeonce import StoreonceManager
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.api.catalyst_gateway import CatalystGateway
from lib.dscc.backup_recovery.protection_policies.api.protection_templates import ProtectionTemplate
from lib.dscc.backup_recovery.vmware_protection.vcenter.api.hypervisor_manager import HypervisorManager
from lib.dscc.backup_recovery.vmware_protection.data_orchestrator.api.software_releases import SoftwareRelease
from lib.common.users.user import User
from lib.common.enums.provided_users import ProvidedUser
from pytest import skip

from lib.dscc.backup_recovery.vmware_protection.common.custom_error_helper import (
    IDNotFoundError,
    NoSuitableVcenterFoundError,
)

logger = logging.getLogger()


class Context:
    def __init__(
        self,
        v_center_type=None,
        test_provided_user=ProvidedUser.user_one,
        skip_inventory_exception=False,
        **overwrite_default,
    ):
        self.config = ConfigManager.get_config()
        ConfigManager.check_and_update_unused_ip_for_psg(self.config)
        self.user = User(user_tag=test_provided_user.value, oauth2_server=self.config["CLUSTER"]["oauth2_server"])

        self.ope = OPE(self.user)

        self.minio = self.config["MINIO"]
        self.minio_bucket_name = self.minio["bucket_name"]

        self.hypervisor_manager = HypervisorManager(self.user)
        self.test_data = self.config[f"TEST-DATA-FOR-{test_provided_user.value}"]
        self.psgw_suffix = "".join(random.choice(string.ascii_letters) for _ in range(10))

        self.excluded_vcenters = (
            overwrite_default["excluded_vcenters"]
            if "excluded_vcenters" in overwrite_default
            else ast.literal_eval(self.config["CLUSTER"]["excluded_vcenters"])
        )

        self.vcenter = self.config[v_center_type] if v_center_type else self.find_vcenter_for_automation()

        logger.info(f"Running tests against vcenter {self.vcenter.name} -> {self.vcenter['ip']}")
        # Get all VCENTER{i} sections into a list
        self.vcenters = [self.config[config_section] for config_section in self.config if "VCENTER" in config_section]

        self.username_read_only_privilege = self.vcenter["username_read_only_privilege"]
        self.username_non_admin_privilege = self.vcenter["username_non_admin_privilege"]

        self.vcenter_name = self.vcenter["ip"]
        self.vcenter_username = self.vcenter["username"]
        self.vcenter_password = self.vcenter["password"]
        self.hypervisor_name = self.vcenter["esxi_host"]
        self.hypervisor_cluster_name = self.vcenter["hypervisor_cluster"]
        self.psg_deploy_folder = self.vcenter["psg_deploy_folder"]
        self.content_library_datastore = self.vcenter["content_library_datastore"]
        self.resource_pools = self.vcenter["resources_pools"]
        self.datastore_name = self.vcenter["datastore"]
        self.datastore_62tb = self.vcenter["datastore_62tb"]
        self.vm_id = overwrite_default["vm_id"] if "vm_id" in overwrite_default else None
        self.vm_template_name = self.config["CLUSTER"]["vm_template_name"]
        self.large_vm_template_name = self.config["CLUSTER"]["large_vm_template_name"]
        self.large_vm_username = self.vcenter["large_vm_username"]
        self.large_vm_password = self.vcenter["large_vm_password"]

        self.array = self.config["ARRAYS"]["array"]
        if "flat_network_support" in self.vcenter and self.vcenter["flat_network_support"] == "yes":
            self.array = self.config["ARRAYS"]["array_flat"]

        self.vm_name = (
            overwrite_default["vm_name"]
            if "vm_name" in overwrite_default
            else f"_{self.vm_template_name}_{self.psgw_suffix}"
        )
        self.asset_type = {"vm": "hybrid-cloud/virtual-machine", "ds": "hybrid-cloud/datastore"}
        self.catalyst_gateway = CatalystGateway(self.user)
        self.software_releases = SoftwareRelease(self.user)
        self.protection_template = ProtectionTemplate(self.user)
        self.minio_client = MinioBuckets()

        try:
            self.vcenter_id = self.hypervisor_manager.get_id(self.vcenter_name, self.hypervisor_manager.get_vcenters())
        except IDNotFoundError:
            if skip_inventory_exception:
                self.vcenter_id = None
            else:
                raise

        self.datastore_id = self.hypervisor_manager.get_datastore_id(self.datastore_name, self.vcenter_name)
        self.content_lib_datastore_id = self.hypervisor_manager.get_datastore_id(
            self.content_library_datastore,
            self.vcenter_name,
        )

        hypervisor_hosts = self.hypervisor_manager.get_hypervisor_hosts()
        if hypervisor_hosts.status_code != codes.ok:
            skip(f"Failed to find Hypervisor host ID for '{self.hypervisor_name}'")

        try:
            self.esxhost_id = self.hypervisor_manager.get_id(self.hypervisor_name, hypervisor_hosts)
        except IDNotFoundError:
            if skip_inventory_exception:
                self.esxhost_id = None
            else:
                raise

        hypervisor_cluster = self.hypervisor_manager.get_hypervisor_clusters()
        try:
            self.hypervisor_cluster_id = self.hypervisor_manager.get_id(
                self.hypervisor_cluster_name,
                hypervisor_cluster,
            )
        except IDNotFoundError:
            if skip_inventory_exception:
                self.hypervisor_cluster_id = None
            else:
                raise

        hypervisor_folders = self.hypervisor_manager.get_hypervisor_folder(vcenter_id=self.vcenter_id)
        try:
            self.hypervisor_folder_id = self.hypervisor_manager.get_folder_id(
                self.psg_deploy_folder,
                hypervisor_folders,
            )
        except IDNotFoundError:
            if skip_inventory_exception:
                self.hypervisor_folder_id = None
            else:
                raise

        hypervisor_resources_pools = self.hypervisor_manager.get_hypervisor_resource_pools(vcenter_id=self.vcenter_id)
        try:
            self.resources_pools_id = self.hypervisor_manager.get_id(
                self.resource_pools,
                hypervisor_resources_pools,
            )
        except IDNotFoundError:
            if skip_inventory_exception:
                self.resources_pools_id = None
            else:
                raise

        self.ope_hostname_prefix = self.config["DATA-ORCHESTRATORS"]["hostname_prefix"]
        self.ope_id = self.hypervisor_manager.get_data_orchestrator_id(hostname_prefix=self.ope_hostname_prefix)
        if not self.ope_id:
            skip(f"Failed to find healthy OPE with given hostname prefix '{self.ope_hostname_prefix}'")
        self.ope_id_assigned_to_vcenter = self.hypervisor_manager.get_ope_id_assigned_to_vcenter(self.vcenter_id)
        self.ope_url = self.config["OVA-TEMPLATE"]["ope_url"]
        self.write_OPE_version_to_file()
        # network test data
        self.gateway = self.test_data["gateway"]
        self.network = self.test_data["network"]
        self.network_ip_range = self.test_data["network_ip_range"]
        self.netmask = self.test_data["netmask"]
        self.network_type = self.test_data["network_type"]

        # network interfaces details
        self.nic_primary_interface = self.config["NETWORK-INTERFACE1"]
        self.nic_data1 = self.config["NETWORK-INTERFACE2"]
        self.nic_data2 = self.config["NETWORK-INTERFACE3"]
        self.nic_data1_ip = None
        self.nic_data2_ip = None

        self.psgw_name = (
            overwrite_default["psgw_name"]
            if "psgw_name" in overwrite_default
            else f'{self.test_data["psgw_name"]}_{self.psgw_suffix}#{self.network}'
        )
        # App data management templates data
        self.local_template = f"{self.test_data['policy_name']}_{self.psgw_suffix}"
        self.network_name = self.hypervisor_manager.get_moref(
            self.test_data["network_name"],
            self.hypervisor_manager.get_networks(self.vcenter_id),
        )
        self.dns = self.test_data["dns"]
        self.dns2 = self.test_data["dns2"]
        self.proxy = self.test_data["proxy"]
        self.port = int(self.test_data["port"])
        self.ntp_server_address = self.test_data["ntp_server_address"]
        self.secondary_psgw_ip = self.test_data["secondary_psgw_ip"]

        # test data
        self.local_template_id = 0
        self.app_data_management_jobs_info = 0

        # size monitoring vms
        self.vm_name_size_monitoring_list = self.vcenter["vm_name_size_monitoring_list"].split(",")

        # large data backup check vms
        self.large_size_data_vm_name_list = self.vcenter["large_size_data_vm_name_list"].split(",")

        self.aws_region = None
        self.template_list = []

        # content library name
        self.content_library = self.config["CONTENT-LIBRARY"]["content_library"]

        # Active Directory credential
        self.ad_username = self.vcenter.get("ad_username")
        self.ad_password = self.vcenter.get("ad_password")

        # last snapshot task id
        self.last_snapshot_task_id = None

        # storeonces data
        if "storeonce" in overwrite_default:
            self.storeonces_config = self.config["STOREONCE_TEST_DATA"]
            self.storeonces_network_address = self.storeonces_config["ip_address"]
            self.secondary_storeonce_ip = self.storeonces_config["secondary_so_ip"]
            self.storeonces_fqdn = self.storeonces_config["fqdn"]
            self.storeonces_admin_username = self.storeonces_config["admin_username"]
            self.storeonces_admin_password = self.storeonces_config["admin_password"]
            self.storeonces_dualauth_username = self.storeonces_config["dualauth_username"]
            self.storeonces_dualauth_password = self.storeonces_config["dualauth_password"]
            storeonce_obj = StoreOnce(
                self.storeonces_network_address, self.storeonces_admin_username, self.storeonces_admin_password
            )
            storeonce_hostname, storeonce_serialnumber = storeonce_obj.get_storeoncename_and_serialnumber()
            self.storeonces_name = storeonce_hostname
            self.storeonces_serial_number = storeonce_serialnumber
            second_so_obj = StoreOnce(
                self.secondary_storeonce_ip, self.storeonces_admin_username, self.storeonces_admin_password
            )
            second_so_name, second_so_serialnumber = second_so_obj.get_storeoncename_and_serialnumber()
            self.second_so_name = second_so_name
            self.second_so_serialnumber = second_so_serialnumber
            self.storeonces_dscc_admin_username = self.storeonces_config["dscc_admin_username"]
            self.storeonces_dscc_admin_password = self.storeonces_config["dscc_admin_password"]
            self.storeonces = StoreonceManager(self.user)

    @retry(
        reraise=True,
        retry=retry_if_exception_type(NoSuitableVcenterFoundError),
        stop=stop_after_delay(300),
        wait=wait_fixed(10),
    )
    def find_vcenter_for_automation(self):
        all_available_online_vcenters = [
            vcenter for vcenter in self.hypervisor_manager.get_vcenters().json().get("items")
        ]
        vcenters_from_variables = [
            self.config[config_section] for config_section in self.config if "VCENTER" in config_section
        ]

        vcenter_names_for_usage = [
            section
            for section in vcenters_from_variables
            if (
                section["ip"]
                in (item["name"] for item in all_available_online_vcenters if str(item["state"]).lower() == "ok")
            )
        ]
        assert len(vcenter_names_for_usage) != 0, (
            f"We didn't get any vcenters with Ok state that are available!"
            f" Online vcenters: (state, vcenter_name) - {[(item['state'], item['name']) for item in all_available_online_vcenters]},"
            f" variable vcenters: {[item['ip'] for item in vcenters_from_variables]}"
        )

        preferred_vcenter_for_tests = [
            section
            for section in vcenters_from_variables
            if (
                (section.name == "VCENTER1" or section.name == "VCENTER_SANITY")
                and section["ip"] not in self.excluded_vcenters
            )
        ]

        if len(preferred_vcenter_for_tests) != 0 and preferred_vcenter_for_tests[0] in vcenter_names_for_usage:
            return preferred_vcenter_for_tests[0]
        else:
            logger.info(all_available_online_vcenters)
            logger.info(vcenter_names_for_usage)
            logger.info(preferred_vcenter_for_tests)
            try:
                return [vcenter for vcenter in vcenter_names_for_usage if vcenter["ip"] not in self.excluded_vcenters][
                    0
                ]
            except IndexError:
                raise NoSuitableVcenterFoundError(self.excluded_vcenters, vcenter_names_for_usage) from None

    def write_OPE_version_to_file(self):
        logger.info("Getting OPE details...")
        response = self.ope.get_ope(self.ope_id).json()
        ope_version = response["softwareVersion"]
        logger.info(f"DO/OPE version: {ope_version}")
        path = os.getcwd()
        with open(path + "/OPE_version.txt", "w") as file:
            logger.info(f"Writing {ope_version} into file...")
            file.write(ope_version)
        logger.info("Writing into file finished.")


class SanityContext(Context):
    def __init__(
        self,
        deploy=False,
        set_static_policy=True,
    ):
        super().__init__(v_center_type="VCENTER_SANITY")
        self.sanity = self.config["SANITY"]
        self.static_policy = self.sanity["static_policy"]
        self.sanity_policy = f"{self.sanity['sanity_policy']}_{self.psgw_suffix}"
        self.static_psgw = self.sanity["static_psgw"]
        if not deploy:
            self.psgw_name = self.static_psgw
        self.local_template = self.static_policy if set_static_policy else self.sanity_policy
        if set_static_policy:
            try:
                self.local_template_id = ProtectionTemplate(self.user).get_protection_template_by_name(
                    self.local_template
                )["id"]
            except KeyError:
                raise Exception(f"Protection policy {self.local_template} not found in the Atlas")
