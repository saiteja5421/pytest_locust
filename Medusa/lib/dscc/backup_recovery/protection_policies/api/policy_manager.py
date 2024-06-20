import logging
import json
from uuid import UUID

from lib.common.enums.asset_info_types import AssetType
from lib.common.enums.backup_consistency import BackupConsistency
from lib.common.common import get, post, patch, delete, put
from lib.common.config.config_manager import ConfigManager
from lib.common.enums.app_type import AppType

from requests import codes, Response

from lib.common.users.user import User

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import ObjectIdType

from lib.dscc.backup_recovery.protection_policies.rest.v1beta1.models.protection_jobs import (
    ProtectionJob,
    ProtectionJobList,
)
from lib.dscc.backup_recovery.protection_policies.payload.post_protection_jobs import (
    PostProtectionJobs,
    PostProtectionJob_NoOverrides,
)
from lib.dscc.backup_recovery.protection_policies.rest.v1beta1.models.protection_policies import (
    ProtectionPolicy,
    ProtectionPolicyList,
)

from lib.dscc.backup_recovery.protection_policies.payload.post_put_patch_protection_policies import (
    Protections,
    Protection,
)
from lib.dscc.tasks.api.tasks import TaskManager
from utils.json_converter import UUIDEncoder

logger = logging.getLogger()


class PolicyManager:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        self.atlantia_api = config["ATLANTIA-API"]
        self.dscc = config["CLUSTER"]
        self.url = f"{self.dscc['atlantia-url']}/api/{self.dscc['version']}"
        self.beta_url = (
            f"{self.dscc['atlantia-url']}/{self.atlantia_api['backup-recovery']}/{self.dscc['beta-version']}"
        )
        self.protection_jobs = self.atlantia_api["protection-jobs"]
        self.protection_policies = self.atlantia_api["protection-policies"]
        self.tasks = TaskManager(user)

    # GET /protection-jobs
    def get_protection_jobs(self) -> ProtectionJobList:
        response: Response = get(self.beta_url, self.protection_jobs, headers=self.user.authentication_header)
        assert response.status_code == codes.ok, response.content
        return ProtectionJobList.from_json(response.text)

    # POST /protection-jobs
    def post_protection_jobs(
        self,
        asset_id: UUID,
        asset_type: str,
        protection_policy_id: UUID,
        backup_id: UUID,
        cloud_backup_id: UUID,
    ) -> str:
        consistency = None if asset_type == AssetType.CSP_VOLUME.value else BackupConsistency.CRASH.value
        payload = PostProtectionJobs(
            asset_id, asset_type, protection_policy_id, backup_id, cloud_backup_id, consistency=consistency
        ).to_json()
        response: Response = post(
            self.beta_url,
            self.protection_jobs,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        assert response.status_code == codes.accepted, response.content
        return self.tasks.get_task_id_from_header(response)

    def post_protection_job(self, asset_id: UUID, asset_type: str, protection_policy_id: UUID) -> str:
        payload = PostProtectionJob_NoOverrides(
            asset_info=ObjectIdType(asset_id, asset_type),
            protection_policy_id=protection_policy_id,
        ).to_json()
        response: Response = post(
            self.url,
            self.protection_jobs,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        assert response.status_code == codes.accepted, response.content
        return self.tasks.get_task_id(response)

    # GET /protection-jobs/{id}
    def get_protection_job(self, protection_job_id: UUID) -> ProtectionJob:
        path = f"{self.protection_jobs}/{protection_job_id}"
        response: Response = get(self.beta_url, path, headers=self.user.authentication_header)
        assert response.status_code == codes.ok, response.content
        return ProtectionJob.from_json(response.text)

    # DELETE /protection-jobs/{id}
    def delete_protection_job(self, protection_job_id: UUID) -> str:
        path = f"{self.protection_jobs}/{protection_job_id}"
        response: Response = delete(self.beta_url, path, headers=self.user.authentication_header)
        assert response.status_code == codes.accepted, response.content
        return self.tasks.get_task_id_from_header(response)

    # No UI element seems to be using this API endpoint. Implement if required.
    def patch_protection_jobs(self):
        pass

    # POST /protection-jobs/{id}/resume
    def resume_protection_job(self, protection_job_id: UUID, schedules_ids: list[int]) -> str:
        path = f"{self.protection_jobs}/{protection_job_id}/resume"
        payload = json.dumps(dict(scheduleIds=schedules_ids))
        response: Response = post(self.beta_url, path, json_data=payload, headers=self.user.authentication_header)
        assert response.status_code == codes.accepted, response.content
        return self.tasks.get_task_id_from_header(response)

    # POST /protection-jobs/{id}/run
    def run_protection_job(self, protection_job_id: UUID, protection_schedule_ids: list[int]) -> str:
        path = f"{self.protection_jobs}/{protection_job_id}/run"

        # dict(Name="group-name"
        payload = json.dumps(dict(scheduleIds=protection_schedule_ids))
        # json.dumps(protection_schedule_ids)

        response: Response = post(self.beta_url, path, json_data=payload, headers=self.user.authentication_header)
        # response: Response = post(self.url, path, headers=self.user.authentication_header)

        assert response.status_code == codes.accepted, response.content
        return self.tasks.get_task_id_from_header(response)

    # POST /protection-jobs/{id}/suspend
    def suspend_protection_job(self, protection_job_id: UUID, schedules_ids: list[int]) -> str:
        path = f"{self.protection_jobs}/{protection_job_id}/suspend"
        payload = json.dumps(dict(scheduleIds=schedules_ids))
        response: Response = post(self.beta_url, path, json_data=payload, headers=self.user.authentication_header)
        assert response.status_code == codes.accepted, response.content
        return self.tasks.get_task_id_from_header(response)

    def get_protection_policy_by_name(self, protection_policy_name: str) -> ProtectionPolicy:
        protection_policy_list: ProtectionPolicyList = self.get_protection_policies()
        try:
            protection_policy = next(
                filter(
                    lambda item: item.name == protection_policy_name,
                    protection_policy_list.items,
                )
            )
            return protection_policy
        except StopIteration:
            logger.warning(f"Protection policy not found with the name: {protection_policy_name}")
            return {}

    def get_protection_jobs_by_protection_policy_id(
        self, protection_policy_id: str, expected_status_code: int = codes.ok
    ) -> ProtectionJobList:
        path: str = f"{self.protection_jobs}?filter=protectionPolicyInfo/id eq {protection_policy_id}"
        response: Response = get(self.beta_url, path, headers=self.user.authentication_header)
        assert (
            response.status_code == expected_status_code
        ), f"No protection jobs associated with protection policy '{protection_policy_id}'"
        return ProtectionJobList.from_json(response.text)

    # /backup-recovery/v1beta1/protection-jobs?filter=assetInfo/id%20eq%20630c62e3-0d9a-5571-b64c-58ea1e8f673a
    def get_protection_job_by_asset_id(self, asset_id: str) -> ProtectionJobList:
        response: Response = get(
            self.beta_url,
            f"{self.protection_jobs}?filter=assetInfo/id eq {asset_id}",
            headers=self.user.authentication_header,
        )
        assert response.status_code == codes.ok, f"Failed to retrive the protection job id associated with {asset_id}"
        return ProtectionJobList.from_json(response.text)

    def get_protection_job_by_asset_name(self, asset_name: str) -> ProtectionJobList:
        response: Response = get(
            self.beta_url,
            f"{self.protection_jobs}?filter=assetInfo/name eq {asset_name}",
            headers=self.user.authentication_header,
        )
        assert response.status_code == codes.ok, f"Failed to retrive the protection job id associated with {asset_name}"
        return ProtectionJobList.from_json(response.text)

    # GET /protection-policies
    def get_protection_policies(self) -> ProtectionPolicyList:
        path = f"{self.protection_policies}?limit=10000"
        response: Response = get(self.beta_url, path, headers=self.user.authentication_header)
        assert response.status_code == codes.ok, response.content
        # an enourmous amount of data in the logs, especially on SCDEV01
        # logger.info(f"Protection Policies = {response.text}")
        return ProtectionPolicyList.from_json(response.text)

    # GET /protection-policies/{id}
    def get_protection_policy(self, protection_policy_id: UUID) -> ProtectionPolicy:
        path = f"{self.protection_policies}/{protection_policy_id}"
        response: Response = get(self.beta_url, path, headers=self.user.authentication_header)
        assert response.status_code == codes.ok, response.content
        return ProtectionPolicy.from_json(response.text)

    # POST /protection-policies/
    def post_protection_policy(
        self,
        name: str,
        protections: list[Protection],
        applicationType: AppType,
    ) -> ProtectionPolicy:
        payload = Protections(protections=protections, name=name, applicationType=applicationType).to_json()
        response: Response = post(
            self.beta_url,
            self.protection_policies,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        assert response.status_code == codes.ok, response.content
        return ProtectionPolicy.from_json(response.text)

    # PATCH /protection-policies/{id}
    def patch_protection_policy(
        self,
        protection_policy_id: UUID,
        name: str,
        protections: list[Protection],
    ) -> ProtectionPolicy:
        for protection in protections:
            protection.type = None
            for schedule in protection.schedules:
                schedule.schedule.activeTime = None
        protections_dict = Protections(protections, name).to_dict()

        def _clean_empty(d):
            if isinstance(d, dict):
                return {k: v for k, v in ((k, _clean_empty(v)) for k, v in d.items()) if v}
            if isinstance(d, list):
                return [v for v in map(_clean_empty, d) if v]
            return d

        protections_dict = _clean_empty(protections_dict)
        payload = json.dumps(protections_dict, cls=UUIDEncoder)
        path = f"{self.protection_policies}/{protection_policy_id}"

        response: Response = patch(
            self.beta_url,
            path,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        assert response.status_code == codes.ok, response.content
        return ProtectionPolicy.from_json(response.text)

    def put_protection_policy(self, policy_id: UUID, name: str, protections: list[Protection], application_type: str):
        for protection in protections:
            protection.id = None
            for schedule in protection.schedules:
                schedule.schedule.activeTime = None

        protections_dict = Protections(protections=protections, name=name, applicationType=application_type).to_dict()

        def _clean_empty(d):
            if isinstance(d, dict):
                return {k: v for k, v in ((k, _clean_empty(v)) for k, v in d.items()) if v}
            if isinstance(d, list):
                return [v for v in map(_clean_empty, d) if v]
            return d

        protections_dict = _clean_empty(protections_dict)
        payload = json.dumps(protections_dict, cls=UUIDEncoder)
        path = f"{self.protection_policies}/{policy_id}"

        response: Response = put(self.beta_url, path, payload, headers=self.user.authentication_header)
        assert response.status_code == codes.ok, response.content
        return ProtectionPolicy.from_json(response.text)

    # PUT /protection-policies/{id}
    def replace_protection_policy(
        self,
        name: str,
        description: str,
        protection_policy_id: UUID,
        protections: list[Protection],
    ) -> ProtectionPolicy:
        payload = Protections(protections=protections, name=name, description=description).to_json()
        path = f"{self.protection_policies}/{protection_policy_id}"
        response: Response = put(
            self.beta_url,
            path,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        assert response.status_code == codes.ok, response.content
        return ProtectionPolicy.from_json(response.text)

    # DELETE /protection-policies/{id}
    def delete_protection_policy(self, protection_policy_id: UUID) -> Response:
        path = f"{self.protection_policies}/{protection_policy_id}"
        response: Response = delete(self.beta_url, path, headers=self.user.authentication_header)
        return response

    def get_protections_jobs_for_the_protection_policy(self, protection_policy_id: UUID) -> ProtectionJobList:
        query_filter = "?filter=protectionPolicyInfo/id eq "
        path = f"{self.protection_jobs}{query_filter}{protection_policy_id}"
        response: Response = get(self.beta_url, path, headers=self.user.authentication_header)
        assert response.status_code == codes.ok
        logger.debug(f"Protection Jobs = {response.text}")
        return ProtectionJobList.from_json(response.text)
