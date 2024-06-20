import logging
from lib.common.config.config_manager import ConfigManager
from json import dumps
from requests import codes

from lib.dscc.backup_recovery.protection_policies.payload.post_new_protection_template import PostNewProtectionTemplate
from lib.dscc.backup_recovery.protection_policies.payload.patch_update_protection_template import (
    PatchUpdateProtectionTemplate,
)
from lib.dscc.backup_recovery.protection_policies.payload.post_protection_policy import PostProtectionPolicy
from lib.dscc.backup_recovery.protection_policies.payload.put_replace_protection_template import (
    PutReplaceProtectionTemplate,
)
from lib.dscc.backup_recovery.vmware_protection.virtual_machines.payload.post_protect_vm import ProtectVM

from lib.common.users.user import User
from lib.common.common import get, post, patch, delete, put

from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs

logger = logging.getLogger()


class ProtectionTemplate:
    """
    Class contains methods to perform CRUD operation using RestAPIs in atlas in DSCC
    """

    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlas_api = config["ATLAS-API"]
        self.dscc = config["CLUSTER"]
        self.backup_recovery_url = f"{self.dscc['url']}/{self.atlas_api['backup_recovery']}/{self.dscc['beta-version']}"
        self.path = self.atlas_api["protection_policies"]
        self.protection_jobs = self.atlas_api["protection_jobs"]

    def get_protection_templates(self, params=None):
        return get(
            self.backup_recovery_url, f"{self.path}?limit=0", params=params, headers=self.user.authentication_header
        )

    def get_protection_template(self, template_id):
        return get(
            self.backup_recovery_url,
            f"{self.path}/{template_id}",
            headers=self.user.authentication_header,
        )

    def get_protection_template_by_name(self, template_name):
        response = self.get_protection_templates()
        if response.status_code == codes.ok:
            try:
                item = next(
                    filter(
                        lambda item: item["name"] == template_name,
                        response.json().get("items"),
                    )
                )
                return item
            except StopIteration:
                logger.info(f"Failed to find protection template with name: {template_name}")
                return {}

    def get_app_data_management_job(self, vm_name):
        return get(
            self.backup_recovery_url,
            f"{self.protection_jobs}?filter=assetInfo/name eq {vm_name}",
            headers=self.user.authentication_header,
        )

    def create_protection_template(
        self,
        name,
        expire_after_unit,
        onprem_expire_value,
        cloud_expire_value,
        recurrence,
        repeat_every,
        onprem_protection_store_id_list,
        cloud_protection_store_id_list,
    ):
        payload = PostProtectionPolicy(
            name,
            expire_after_unit,
            onprem_expire_value,
            cloud_expire_value,
            recurrence,
            repeat_every,
            onprem_protection_store_id_list,
            cloud_protection_store_id_list,
        )
        return post(
            self.backup_recovery_url,
            self.path,
            json_data=payload.create(),
            headers=self.user.authentication_header,
        )

    def create_protection_template_for_storeonce(
        self,
        name,
        expire_after_unit,
        onprem_expire_value,
        cloud_expire_value,
        recurrence,
        repeat_every,
        onprem_protection_store_id_list,
        cloud_protection_store_id_list,
    ):
        """This method is to create protection policy with local and cloud  schedules for storeonce.
        Args:
            name (string): User defined name of the protection policy.
            expire_after_unit (enum): HOURS, DAYS, WEEKS, MONTHS, YEARS Accepted units.
            expire_after_value (integer): value should be >=1
            recurrence (enum): HOURS, DAYS, WEEKS, MONTHS, YEARS Accepted units.
            repeat_every (integer): value should be >=1
            onprem_protection_store_id_list (uuid): UUID string uniquely identifying the protection store for onprem schedule.
            cloud_protection_store_id_list (uuid): list of UUID string uniquely identifying the protection store for cloud schedule.
        Returns:
            this method returns response from post call for protection-policies
        """
        storeonce_payload = PostProtectionPolicy(
            name,
            expire_after_unit,
            onprem_expire_value,
            cloud_expire_value,
            recurrence,
            repeat_every,
            onprem_protection_store_id_list,
            cloud_protection_store_id_list,
        )
        return post(
            self.backup_recovery_url,
            self.path,
            json_data=storeonce_payload.create_storeonce_payload(),
            headers=self.user.authentication_header,
        )

    def create_protection_template_with_multiple_cloud_regions(
        self,
        name,
        expire_after_unit,
        onprem_expire_value,
        cloud_expire_value,
        recurrence,
        repeat_every,
        onprem_protection_store_id_list,
        cloud_protection_store_id_list,
    ):
        """This method is to create protection policy with multiple cloud schedules in it.
        Args:
            name (string): User defined name of the protection policy.
            expire_after_unit (enum): HOURS, DAYS, WEEKS, MONTHS, YEARS Accepted units.
            expire_after_value (integer): value should be >=1
            recurrence (enum): HOURS, DAYS, WEEKS, MONTHS, YEARS Accepted units.
            repeat_every (integer): value should be >=1
            onprem_protection_store_id_list (uuid): UUID string uniquely identifying the protection store for onprem schedule.
            cloud_protection_store_id_list (uuid): list of UUID string uniquely identifying the protection store for cloud schedule.
        Returns:
            this method returns response from post call for protection-policies
        """
        payload = PostProtectionPolicy(
            name,
            expire_after_unit,
            onprem_expire_value,
            cloud_expire_value,
            recurrence,
            repeat_every,
            onprem_protection_store_id_list,
            cloud_protection_store_id_list,
        )
        return post(
            self.backup_recovery_url,
            self.path,
            json_data=payload.create(),
            headers=self.user.authentication_header,
        )

    def create_protection_template_with_multiple_cloud_regions_for_storeonce(
        self,
        name,
        expire_after_unit,
        onprem_expire_value,
        cloud_expire_value,
        recurrence,
        repeat_every,
        onprem_protection_store_id_list,
        cloud_protection_store_id_list,
    ):
        """This method is to create protection policy with multiple cloud schedules in it.
        Args:
            name (string): User defined name of the protection policy.
            expire_after_unit (enum): HOURS, DAYS, WEEKS, MONTHS, YEARS Accepted units.
            expire_after_value (integer): value should be >=1
            recurrence (enum): HOURS, DAYS, WEEKS, MONTHS, YEARS Accepted units.
            repeat_every (integer): value should be >=1
            onprem_protection_store_id_list (uuid): UUID string uniquely identifying the protection store for onprem schedule.
            cloud_protection_store_id_list (uuid): list of UUID string uniquely identifying the protection store for cloud schedule.
        Returns:
            this method returns response from post call for protection-policies
        """
        payload = PostProtectionPolicy(
            name,
            expire_after_unit,
            onprem_expire_value,
            cloud_expire_value,
            recurrence,
            repeat_every,
            onprem_protection_store_id_list,
            cloud_protection_store_id_list,
        )
        return post(
            self.backup_recovery_url,
            self.path,
            json_data=payload.create_storeonce_payload(),
            headers=self.user.authentication_header,
        )

    def replace_protection_template(
        self,
        template_id,
        name,
        protections_id,
        activeFromTime,
        activeUntilTime,
        recurrence,
        every,
        protection_type,
        description=None,
        copyPoolId=None,
        expireAfter_unit=None,
        expireAfter_value=None,
        lockFor_unit=None,
        lockFor_value=None,
        schedule_name=None,
        pattern_format=None,
        on=None,
        startTime=None,
        sourceProtectionScheduleId=None,
        verify=None,
    ):
        payload = PutReplaceProtectionTemplate(
            name,
            protections_id,
            activeFromTime,
            activeUntilTime,
            recurrence,
            every,
            protection_type,
            description,
            copyPoolId,
            expireAfter_unit,
            expireAfter_value,
            lockFor_unit,
            lockFor_value,
            schedule_name,
            pattern_format,
            on,
            startTime,
            sourceProtectionScheduleId,
            verify,
        )
        return put(
            self.backup_recovery_url,
            f"{self.path}/{template_id}",
            json_data=dumps(payload.update()),
            headers=self.user.authentication_header,
        )

    def delete_protection_template(self, template_id):
        return delete(
            self.backup_recovery_url,
            f"{self.path}/{template_id}",
            headers=self.user.authentication_header,
        )

    def update_protection_template(
        self,
        schedules_id,
        activeFromTime,
        activeUntilTime,
        recurrence,
        every,
        description=None,
        name=None,
        protections_id=None,
        expireAfter_unit=None,
        expireAfter_value=None,
        lockFor_unit=None,
        lockFor_value=None,
        schedules_name=None,
        pattern_format=None,
        on=None,
        startTime=None,
    ):
        payload = PatchUpdateProtectionTemplate(
            schedules_id,
            activeFromTime,
            activeUntilTime,
            recurrence,
            every,
            description,
            name,
            protections_id,
            expireAfter_unit,
            expireAfter_value,
            lockFor_unit,
            lockFor_value,
            schedules_name,
            pattern_format,
            on,
            startTime,
        )
        return patch(
            self.backup_recovery_url,
            self.path,
            json_data=payload.update(),
            headers=self.user.authentication_header,
        )

    def post_protect_vm(
        self,
        asset_name,
        asset_type,
        asset_id,
        template_id,
        snapshot_id,
        local_backup_id,
        cloud_backup_id,
        backup_granularity_type,
    ):
        payload = ProtectVM(
            asset_name,
            asset_type,
            asset_id,
            template_id,
            snapshot_id,
            local_backup_id,
            cloud_backup_id,
            backup_granularity_type,
        )
        return post(
            self.backup_recovery_url,
            self.protection_jobs,
            json_data=payload.create(),
            headers=self.user.authentication_header,
        )

    def post_protect_vm_storeonce(
        self,
        asset_name,
        asset_type,
        asset_id,
        template_id,
        local_backup_id,
        cloud_backup_id,
        backup_granularity_type,
    ):
        """
        this protectvm class need snapshot_id for storeonce we not creating  snapshot  so
        assign to  snaphot_id value to  none
        """
        snapshot_id = None
        payload = ProtectVM(
            asset_name,
            asset_type,
            asset_id,
            template_id,
            snapshot_id,
            local_backup_id,
            cloud_backup_id,
            backup_granularity_type,
        )
        return post(
            self.backup_recovery_url,
            self.protection_jobs,
            json_data=payload.create_storeonce(),
            headers=self.user.authentication_header,
        )

    def post_backup_run(
        self, app_data_management_job_id, backup_type, schedule_ids=BackupTypeScheduleIDs.cloud, multiple_stores=False
    ):
        if multiple_stores:
            payload = {"scheduleIds": schedule_ids}
        else:
            payload = {"scheduleIds": backup_type.value}
        path = f"{self.protection_jobs}/{app_data_management_job_id}/run"
        return post(
            self.backup_recovery_url,
            path,
            json_data=dumps(payload),
            headers=self.user.authentication_header,
        )

    def unprotect_vm(self, app_data_management_job_id):
        path = f"{self.protection_jobs}/{app_data_management_job_id}"
        return delete(self.backup_recovery_url, path, headers=self.user.authentication_header)

    def delete_policy(self, template_id):
        return delete(
            self.backup_recovery_url,
            f"{self.path}/{template_id}",
            headers=self.user.authentication_header,
        )
