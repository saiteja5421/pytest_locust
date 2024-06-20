"""
Class to make API calls to:
https://pages.github.hpe.com/cloud/storage-api/backup-recovery/v1beta1/#tag/Granular-File-Level-Recovery
APIs
"""

import logging
from typing import Union
import requests
from requests import Response
from lib.common.common import get_task_id_from_header, post
from lib.common.config.config_manager import ConfigManager
from lib.common.users.user import User
from lib.dscc.backup_recovery.aws_protection.gfrs.domain_models.gfrs_models import (
    LocationModel,
    PostRestoreCSPFileSystemInfoModel,
)
from lib.dscc.backup_recovery.aws_protection.gfrs.models.gfrs_error_response import GFRSErrorResponse

from lib.dscc.backup_recovery.aws_protection.gfrs.payload.file_system_info_v1beta1_filepoc import (
    PostRestoreCSPFileSystemInfo,
)

logger = logging.getLogger()


class GFRSDataProtectionManagerV1Beta1Filepoc:
    def __init__(self, user: User):
        self.user = user
        config = ConfigManager.get_config()
        # blocks from INI file
        self.atlantia_api = config["ATLANTIA-API"]
        self.dscc = config["CLUSTER"]
        # https://scdev01-app.qa.cds.hpe.com/backup-recovery/v1beta1
        self.beta_url = (
            f"{self.dscc['atlantia-url']}/{self.atlantia_api['backup-recovery']}/{self.dscc['beta-version']}"
        )
        self.csp_volume_backups = self.atlantia_api["csp-volume-backups"]
        self.csp_machine_instance_backups = self.atlantia_api["csp-machine-instance-backups"]
        self.restore_files = self.atlantia_api["restore-files"]

    # POST /v1beta1/csp-machine-instance-backups/{backupId}/restore-files
    def restore_csp_machine_instance_files_folders(
        self,
        csp_backup_id: str,
        restore_info: PostRestoreCSPFileSystemInfoModel,
        response_code=requests.codes.accepted,
    ) -> Union[LocationModel, GFRSErrorResponse]:
        restore_info_payload = PostRestoreCSPFileSystemInfo.from_domain_model(restore_info)
        payload = restore_info_payload.to_json()
        path: str = f"{self.csp_machine_instance_backups}/{csp_backup_id}/{self.restore_files}"
        response: Response = post(
            self.beta_url,
            path,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        assert response.status_code == response_code, response.text
        if response.status_code == requests.codes.accepted:
            # assuming that the restore operation will also create a task, that's why returning both
            return LocationModel(response.json()["targetLocations"][0], get_task_id_from_header(response))
        else:
            return GFRSErrorResponse(**response.json())

    # POST /v1beta1/csp-volume-backups/{backupId}/restore-files
    def restore_csp_volume_files_folders(
        self,
        csp_backup_id: str,
        restore_info: PostRestoreCSPFileSystemInfoModel,
        response_code=requests.codes.accepted,
    ) -> Union[LocationModel, GFRSErrorResponse]:
        restore_info_payload = PostRestoreCSPFileSystemInfo.from_domain_model(restore_info)
        payload = restore_info_payload.to_json()
        path: str = f"{self.csp_volume_backups}/{csp_backup_id}/{self.restore_files}"
        response: Response = post(
            self.beta_url,
            path,
            json_data=payload,
            headers=self.user.authentication_header,
        )
        assert response.status_code == response_code, response.text
        if response.status_code == requests.codes.accepted:
            # assuming that the restore operation will also create a task, that's why returning both
            return LocationModel(response.json()["targetLocations"][0], get_task_id_from_header(response))
        else:
            return GFRSErrorResponse(**response.json())
