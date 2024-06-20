import logging
from json import dumps
from requests import codes
from random import choice
from time import sleep
from datetime import datetime, timedelta

from lib.dscc.backup_recovery.vmware_protection.data_orchestrator.api.ope import OPE
from lib.common.common import get, post, delete, patch
from lib.common.enums.restore_type import RestoreType
from lib.common.enums.backup_type_param import BackupTypeParam
from lib.common.users.user import User
from lib.dscc.backup_recovery.vmware_protection.data_orchestrator.payload.ope import RegisterOPE
from lib.dscc.backup_recovery.vmware_protection.vcenter.payload.post_vcenter import (
    VCenterCredentials,
    PostCreateVcenter,
)
from lib.dscc.backup_recovery.vmware_protection.virtual_machines.payload.post_restore_vm import (
    VmInfo,
    PostRestoreNewVMbackup,
    PostRestoreNewVMsnapshot,
    PostRestoreExistingVMbackup,
    PostRestoreExistingVMsnapshot,
)
from lib.common.config.config_manager import ConfigManager
from lib.dscc.backup_recovery.vmware_protection.common.custom_error_helper import IDNotFoundError, VcenterNotFoundError
from utils.timeout_manager import TimeoutManager

logger = logging.getLogger()


class HypervisorManager:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlas_api = config["ATLAS-API"]
        self.dscc = config["CLUSTER"]
        self.hybrid_cloud = self.atlas_api["hybrid_cloud"]
        self.hybrid_cloud_url = f"{self.dscc['url']}/{self.hybrid_cloud}/{self.dscc['beta-version']}"
        self.backup_recovery_url = f"{self.dscc['url']}/{self.atlas_api['backup_recovery']}/{self.dscc['beta-version']}"
        self.backup_recovery_alpha1_url = (
            f"{self.dscc['url']}/{self.atlas_api['backup_recovery']}/{self.dscc['alpha1-version']}"
        )
        self.vcenters_path = self.atlas_api["vcenter"]
        self.datastores_path = self.atlas_api["datastores"]
        self.vm_path = self.atlas_api["virtual_machines"]
        self.hosts = self.atlas_api["hypervisors"]
        self.hypervisor_hosts = self.atlas_api["hypervisor_hosts"]
        self.hypervisor_cluster = self.atlas_api["hypervisor_cluster"]
        self.networks = self.atlas_api["networks"]
        self.ope = OPE(self.user)
        self.do = self.atlas_api["ope"]

    def get_vcenters(self):
        return get(self.hybrid_cloud_url, self.vcenters_path, headers=self.user.authentication_header)

    def get_vcenter(self, vcenter_id: str):
        return get(
            self.hybrid_cloud_url,
            f"{self.vcenters_path}/{vcenter_id}",
            headers=self.user.authentication_header,
        )

    def get_vcenter_by_name(self, name):
        response = self.get_vcenters()
        assert response.status_code == codes.ok, f"failed with status code: {response.status_code} and {response.text}"
        try:
            item = next(
                filter(
                    lambda item: item["name"] == name,
                    response.json().get("items") if response.json().get("items") else [],
                )
            )
            return item
        except StopIteration:
            raise VcenterNotFoundError(name) from None

    def check_vcenter_already_registered(self, vcenter_name):
        response = self.get_vcenters()
        assert response.status_code == codes.ok, f"failed with status code: {response.status_code} and {response.text}"
        registered_vcenters = response.json().get("items")
        registered = False
        for reg_vcenter in registered_vcenters:
            if reg_vcenter["name"] == vcenter_name:
                logger.info(f"{vcenter_name} already registered")
                registered = True
                return registered
        logger.info(f"{vcenter_name} not registered")
        return registered

    def get_vcenter_state_by_id(self, vcenter_id):
        response = self.get_vcenter(vcenter_id)
        assert response.status_code == codes.ok, f"failed with status code: {response.status_code} and {response.text}"
        return response.json().get("state")

    def get_vcenter_state_by_name(self, vcenter_name):
        response = self.get_vcenter_by_name(vcenter_name)
        assert response.status_code == codes.ok, f"failed with status code: {response.status_code} and {response.text}"
        return response.json().get("state")

    def get_datastores(self):
        return get(
            self.hybrid_cloud_url,
            f"{self.datastores_path}?limit=1000",
            headers=self.user.authentication_header,
        )

    def get_datastore(self, datastore_id):
        return get(
            self.hybrid_cloud_url,
            f"{self.datastores_path}/{datastore_id}",
            headers=self.user.authentication_header,
        )

    def get_datastore_id(self, datastore_name, vcenter_name):
        datastores = self.get_datastores()
        assert datastores.status_code == codes.ok

        # Sometimes 'items' value returned as None, Added check here to use [] instead
        datastores = datastores.json().get("items") if datastores.json().get("items") else []
        for item in datastores:
            if item["name"] == datastore_name and item["hypervisorManagerInfo"]["name"] == vcenter_name:
                return item["id"]
        else:
            logger.warning(f"Failed to find datastore ID with name '{datastore_name}' under vcenter '{vcenter_name}'")

    def get_networks(self, vcenter_id):
        return get(
            self.hybrid_cloud_url,
            f"{self.vcenters_path}/{vcenter_id}/{self.networks}",
            headers=self.user.authentication_header,
        )

    def get_moref(self, name, resp):
        if resp.status_code == codes.ok:
            resp_body = resp.json()
            for item in resp_body["items"]:
                if item["name"] == name:
                    return item["appInfo"]["vmware"]["moref"]

    def get_hypervisors(self, vcenter_id):
        return get(
            self.hybrid_cloud_url,
            f"{self.vcenters_path}/{vcenter_id}/{self.hosts}",
            headers=self.user.authentication_header,
        )

    def get_hypervisor_hosts(self):
        return get(
            self.hybrid_cloud_url,
            f"{self.hypervisor_hosts}?offset=0&limit=500",
            headers=self.user.authentication_header,
        )

    def get_hypervisor_clusters(self):
        return get(
            self.hybrid_cloud_url,
            f"{self.hypervisor_cluster}?offset=0&limit=500",
            headers=self.user.authentication_header,
        )

    def get_hypervisor_folder(self, vcenter_id):
        return get(
            self.hybrid_cloud_url,
            f"{self.vcenters_path}/{vcenter_id}/folders",
            headers=self.user.authentication_header,
        )

    def get_hypervisor_resource_pools(self, vcenter_id):
        return get(
            self.hybrid_cloud_url,
            f"{self.vcenters_path}/{vcenter_id}/resource-pools",
            headers=self.user.authentication_header,
        )

    def get_vms(self):
        return get(
            self.hybrid_cloud_url,
            f"{self.vm_path}?limit=1000",
            headers=self.user.authentication_header,
        )

    def get_vm_info(self, vm_id):
        return get(
            self.hybrid_cloud_url,
            f"{self.vm_path}/{vm_id}",
            headers=self.user.authentication_header,
        )

    @staticmethod
    def get_id(name, response):
        logger.info(f"Getting ID of {name}...")
        assert response.status_code == codes.ok, f"Status code: {response.status_code} => {response.text}"
        try:
            found_item = next(
                filter(
                    lambda item: item["name"] == name and str(item["state"]).lower() == "ok",
                    response.json().get("items") if response.json().get("items") else [],
                )
            )
            logger.info("Got the ID:" + str(found_item["id"]) + f" for {name} in the response")
            return found_item["id"]
        except StopIteration:
            logger.warning(f"ID of {name} not found.")
            raise IDNotFoundError(name) from None

    @staticmethod
    def get_folder_id(name, response):
        logger.info(f"Getting ID of {name}...")
        assert response.status_code == codes.ok, f"Status code: {response.status_code} => {response.text}"
        try:
            found_item = next(
                filter(
                    lambda item: item["name"] == name,
                    response.json().get("items") if response.json().get("items") else [],
                )
            )
            logger.info("Got the ID:" + str(found_item["id"]) + f" for {name} in the response")
            return found_item["id"]
        except StopIteration:
            logger.warning(f"folder ID of {name} not found.")
            raise IDNotFoundError(name) from None

    def get_all_vcenter_names_assigned_to_DO(self, do_id):
        response = self.get_vcenters()
        assert response.status_code == codes.ok, f"Status code: {response.status_code} => {response.text}"

        found_item = filter(
            lambda item: item["dataOrchestratorInfo"]["id"] == do_id and str(item["state"]).lower() == "ok",
            response.json().get("items"),
        )
        return [item["name"] for item in found_item]

    def get_backups(self, asset_id, backup_type):
        return get(
            self.backup_recovery_url,
            f"{self.vm_path}/{asset_id}/{backup_type}",
            headers=self.user.authentication_header,
        )

    def change_expiration(self, asset_id, backup_id, backup_name):
        # Making expiration time of backups to 2 minutes more than current time.
        expiration_time = f"{(datetime.now() + timedelta(minutes=2)).isoformat()}"
        expiration_time = expiration_time[:-3] + "Z"
        # Initializing new backup name
        new_backup_name = f"Updated_{backup_name}"
        payload = dumps(
            {"description": "API automation testing", "expiresAt": expiration_time, "name": new_backup_name}
        )
        return patch(
            self.backup_recovery_url,
            f"{self.vm_path}/{asset_id}/backups/{backup_id}",
            json_data=payload,
            headers=self.user.authentication_header,
        )

    def delete_backup(self, asset_id, backup_id, backup_type):
        return delete(
            self.backup_recovery_url,
            f"{self.vm_path}/{asset_id}/{backup_type}/{backup_id}",
            headers=self.user.authentication_header,
        )

    def unregister_vcenter(self, vcenter_id, force: bool = False):
        return delete(
            self.backup_recovery_alpha1_url,
            f"{self.vcenters_path}/{vcenter_id}?force={force}",
            headers=self.user.authentication_header,
        )

    def register_ope(self, sid, ope_name):
        payload = RegisterOPE(ope_name, sid).to_json()
        return post(
            self.backup_recovery_url,
            "data-orchestrators",
            json_data=payload,
            headers=self.user.authentication_header,
        )

    def get_data_orchestrator_id(self, hostname_prefix=None):
        response = self.ope.get_all_ope()
        if response.status_code == codes.ok:
            content = response.json()
            if content["total"] > 0:
                for item in content["items"][::-1]:
                    if item["state"].lower() == "ok" and item["status"].lower() == "ok":
                        ope_hostname = item.get("interfaces", {}).get("network", {}).get("hostname", "")
                        if not hostname_prefix:
                            return item["id"]

                        if ope_hostname.startswith(hostname_prefix):
                            logger.info(f"Found {ope_hostname} with prefix {hostname_prefix}")
                            return item["id"]
                        else:
                            logger.debug(f"OPE '{ope_hostname}' doesn't match with prefix '{hostname_prefix}'")
            else:
                return None
        else:
            logger.warning(f"Fail to get the list of data orchestrators available in the cluster: {response.content}")
            return None

    def get_data_orchestrator_ip(self, hostname_prefix=None):
        """This method fetches the Data Orchestrator IP

        Args:
            hostname_prefix (string, optional): DO hostname. Defaults to None.

        Returns:
            string: IP of data Orchestrator
        """
        response = self.ope.get_all_ope()
        if response.status_code == codes.ok:
            content = response.json()
            if content["total"] > 0:
                for item in content["items"][::-1]:
                    if item["state"].lower() == "ok" and item["status"].lower() == "ok":
                        ope_hostname = item.get("interfaces", {}).get("network", {}).get("hostname", "")
                        if not hostname_prefix:
                            return item.get("interfaces", {}).get("network", {}).get("nic", [])[0]["networkAddress"]

                        if ope_hostname.startswith(hostname_prefix):
                            logger.info(f"Found {ope_hostname} with prefix {hostname_prefix}")
                            return item.get("interfaces", {}).get("network", {}).get("nic", [])[0]["networkAddress"]
                        else:
                            logger.debug(f"OPE '{ope_hostname}' doesn't match with prefix '{hostname_prefix}'")
            else:
                return None
        else:
            logger.warning(f"Fail to get the list of data orchestrators available in the cluster: {response.content}")
            return None

    def register_vcenter(self, vcenter_name, network_address, username, password, ope_id):
        credentials = VCenterCredentials(username, password)
        payload = PostCreateVcenter(vcenter_name, network_address, credentials, ope_id).to_json()
        return post(
            self.backup_recovery_alpha1_url,
            f"{self.vcenters_path}",
            json_data=payload,
            headers=self.user.authentication_header,
        )

    def refresh_vcenter(self, vcenter_id):
        # eg resource_uri="/hypervisor-managers/20fe95b4-6132-429f-ba6d-faf805812d48"
        payload = {"fullRefresh": True}
        path = f"{self.vcenters_path}/{vcenter_id}/refresh"
        return post(
            self.hybrid_cloud_url,
            path,
            json_data=dumps(payload),
            headers=self.user.authentication_header,
        )

    def get_ope_id_assigned_to_vcenter(self, vcenter_id: str):
        response_vcenter = self.get_vcenter(vcenter_id)
        if response_vcenter.status_code == codes.ok:
            return response_vcenter.json().get("dataOrchestratorInfo").get("id")
        else:
            return None

    def restore_vm(
        self,
        vm_id,
        backup_id,
        restore_type,
        backup_type,
        name=False,
        datastore_id=False,
        host_id=False,
        power_on=True,
    ):
        if restore_type == RestoreType.new.value:
            vminfo = VmInfo(name, host_id, power_on, datastore_id)
            if backup_type != "snapshot":
                payload = PostRestoreNewVMbackup(backup_id, restore_type, vminfo).to_json()
            else:
                payload = PostRestoreNewVMsnapshot(backup_id, restore_type, vminfo).to_json()
            return post(
                self.backup_recovery_url,
                f"{self.vm_path}/{vm_id}/restore",
                json_data=payload,
                headers=self.user.authentication_header,
            )
        elif restore_type == RestoreType.existing.value:
            if backup_type != "snapshot":
                payload = PostRestoreExistingVMbackup(backup_id, restore_type).to_json()
            else:
                payload = PostRestoreExistingVMsnapshot(backup_id, restore_type).to_json()
            return post(
                self.backup_recovery_url,
                f"{self.vm_path}/{vm_id}/restore",
                json_data=payload,
                headers=self.user.authentication_header,
            )

    def get_backup_id(self, asset_id, backup_type):
        backup_ids: list["str"] = list()
        backups = "backups"
        snapshots = "snapshots"
        backup_types = {"cloud": "CLOUD_BACKUP", "local": "BACKUP"}
        if backup_type != "snapshot":
            response = self.get_backups(asset_id, backups)
            backups = response.json()
            if backups["total"] != 0:
                for backup in backups.get("items"):
                    if backup.get("state") != "OK" or backup.get("status") != "OK":
                        logger.warn(f"Backup name: {backup.get('name')} with state {backup.get('state')}. Skipping..")
                        continue
                    if backup.get("backupType") == backup_types.get(backup_type):
                        backup_ids.append(backup["id"])
            else:
                logger.debug(f"{backup_type} backup not found for {asset_id}. Response: {response.text}")
        else:
            response = self.get_backups(asset_id, snapshots)
            backups = response.json()
            if backups["total"] != 0:
                for backup in backups.get("items"):
                    backup_ids.append(backup["id"])
        return choice(backup_ids) if backup_ids else None

    def change_user_on_vcenter(self, new_vcenter_username, new_vcenter_user_password, vcenter_ip, vcenter_id):
        payload = {
            "credentials": {
                "password": new_vcenter_user_password,
                "username": new_vcenter_username,
            },
            "networkAddress": vcenter_ip,
        }
        return patch(
            self.backup_recovery_alpha1_url,
            f"{self.vcenters_path}/{vcenter_id}",
            json_data=dumps(payload),
            headers=self.user.authentication_header,
        )

    def get_backup_count(self, asset_id, backup_type):
        count: int = 0
        response = self.get_backups(asset_id, BackupTypeParam.backups.value)
        if response.status_code == codes.ok:
            backups = response.json()
            if backups["total"] > 0:
                for backup in backups["items"]:
                    if backup["backupType"] == backup_type:
                        count += 1
        return count

    def wait_for_backup_to_finish(
        self,
        initial_count,
        asset_id,
        backup_type,
        timeout=TimeoutManager.create_backup_timeout,
    ):
        count: int = 0
        while timeout > 0:
            count = self.get_backup_count(asset_id, backup_type)
            sleep(5)
            if count > initial_count:
                break
            timeout -= 5
        return count
