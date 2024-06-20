"""
Class to make API calls to:
https://pages.github.hpe.com/cloud/storage-api/backup-recovery/v1beta1/#tag/Granular-File-Level-Recovery
APIs
"""

import logging
from typing import Union

import requests
from requests import Response
from lib.common.common import get, post, delete, get_task_id_from_header
from lib.common.config.config_manager import ConfigManager
from lib.common.users.user import User

# domain models
from lib.dscc.backup_recovery.aws_protection.gfrs.domain_models.gfrs_models import PostCSPFileSystemInfoModel
from lib.dscc.backup_recovery.aws_protection.gfrs.domain_models.csp_indexed_file_system_info_model import (
    CSPIndexedFileSystemInfoListModel,
)
from lib.dscc.backup_recovery.aws_protection.gfrs.domain_models.csp_indexed_files_and_folders_info_model import (
    CSPIndexedFilesAndFoldersSystemInfoListModel,
)

from lib.dscc.backup_recovery.aws_protection.gfrs.models.csp_indexed_file_system_info_v1beta1_filepoc import (
    CSPIndexedFileSystemInfoList,
)
from lib.dscc.backup_recovery.aws_protection.gfrs.models.csp_indexed_files_and_folders_info_v1beta1_filepoc import (
    CSPIndexedFilesAndFoldersSystemInfoList,
)
from lib.dscc.backup_recovery.aws_protection.gfrs.payload.file_system_info_v1beta1_filepoc import PostCSPFileSystemInfo

from lib.dscc.backup_recovery.aws_protection.gfrs.models.gfrs_error_response import GFRSErrorResponse
from lib.common.enums.csp_resource_type import CSPResourceType

logger = logging.getLogger()


class GFRSIndexManager:
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
        # https://scdev01-app.qa.cds.hpe.com/backup-recovery/v1beta2
        self.beta2_url = (
            f"{self.dscc['atlantia-url']}/{self.atlantia_api['backup-recovery']}/{self.dscc['beta2-version']}"
        )
        self.csp_volume_backups = self.atlantia_api["csp-volume-backups"]
        self.csp_machine_instance_backups = self.atlantia_api["csp-machine-instance-backups"]
        self.index_files = self.atlantia_api["index-files"]
        self.indexed_filesystems = self.atlantia_api["indexed-filesystems"]
        self.indexed_files = self.atlantia_api["indexed-files"]

    # POST /v1beta1/csp-volume-backups/{backupId}/index-files
    def index_guest_files_on_csp_volume_backup(
        self,
        csp_backup_id: str,
        post_file_system_info: PostCSPFileSystemInfoModel = "{}",
        response_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, GFRSErrorResponse]:

        if isinstance(post_file_system_info, PostCSPFileSystemInfoModel):
            payload_json = PostCSPFileSystemInfo.from_domain_model(domain_model=post_file_system_info).to_json()
        else:
            payload_json = post_file_system_info

        path: str = f"{self.csp_volume_backups}/{csp_backup_id}/{self.index_files}"
        response: Response = post(
            self.beta_url,
            path,
            json_data=payload_json,
            headers=self.user.authentication_header,
        )
        assert response.status_code == response_code, response.text
        if response.status_code == requests.codes.accepted:
            return get_task_id_from_header(response)
        else:
            return GFRSErrorResponse(**response.json())

    # POST /v1beta1/csp-machine-instances/{backupId}/index-files
    def index_guest_files_on_csp_machine_instance_backup(
        self,
        csp_backup_id: str,
        post_file_system_info: PostCSPFileSystemInfoModel = "{}",
        response_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, GFRSErrorResponse]:

        if isinstance(post_file_system_info, PostCSPFileSystemInfoModel):
            payload_json = PostCSPFileSystemInfo.from_domain_model(domain_model=post_file_system_info).to_json()
        else:
            payload_json = post_file_system_info

        path: str = f"{self.csp_machine_instance_backups}/{csp_backup_id}/{self.index_files}"
        response: Response = post(
            self.beta_url,
            path,
            json_data=payload_json,
            headers=self.user.authentication_header,
        )
        assert response.status_code == response_code, response.text
        if response.status_code == requests.codes.accepted:
            return get_task_id_from_header(response)
        else:
            return GFRSErrorResponse(**response.json())

    # GET /v1beta2/indexed-filesystems (FLR V2)
    def get_indexed_file_system_info_for_backup(
        self,
        csp_asset_type: CSPResourceType,
        csp_asset_id: str,
        csp_backup_id: str,
    ) -> CSPIndexedFileSystemInfoListModel:
        path: str = (
            f"{self.indexed_filesystems}?asset-type={csp_asset_type.value}&asset-id={csp_asset_id}&backup-id={csp_backup_id}"
        )
        response: Response = get(self.beta2_url, path=path, headers=self.user.authentication_header)
        assert response.status_code == requests.codes.ok, response.content
        csp_index_filesystem_list: CSPIndexedFileSystemInfoList = CSPIndexedFileSystemInfoList.from_json(response.text)
        return csp_index_filesystem_list.to_domain_model()

    # GET /v1beta1/indexed-filesystems
    def get_indexed_file_system_info_for_snapshot(
        self,
        csp_snapshot_id: str,
    ) -> CSPIndexedFileSystemInfoListModel:
        path: str = f"{self.indexed_filesystems}?snapshot={csp_snapshot_id}"
        response: Response = get(self.beta_url, path=path, headers=self.user.authentication_header)
        assert response.status_code == requests.codes.ok, response.content
        csp_index_filesystem_list: CSPIndexedFileSystemInfoList = CSPIndexedFileSystemInfoList.from_json(response.text)
        return csp_index_filesystem_list.to_domain_model()

    # GET /v1beta2/indexed-files (FLR V2)
    def get_files_and_folders_info_from_backup(
        self,
        csp_backup_id: str,
        offset: int = 0,
        limit: int = 1000,
    ) -> CSPIndexedFilesAndFoldersSystemInfoListModel:
        filter: str = f"?backup-id={csp_backup_id}&limit={limit}&offset={offset}"
        path: str = f"{self.indexed_files}/{filter}"
        response: Response = get(self.beta2_url, path=path, headers=self.user.authentication_header)
        assert response.status_code == requests.codes.ok, response.content
        csp_indexed_files: CSPIndexedFilesAndFoldersSystemInfoList = CSPIndexedFilesAndFoldersSystemInfoList.from_json(
            response.text
        )
        return csp_indexed_files.to_domain_model()

    # GET /v1beta1/indexed-files
    def get_files_and_folders_info_from_snapshot(
        self,
        csp_snapshot_id: str,
        root_path: str,
        offset: int = 0,
        limit: int = 1000,
    ) -> CSPIndexedFilesAndFoldersSystemInfoListModel:
        filter: str = f"?snapshot={csp_snapshot_id}&root-path={root_path}&limit={limit}&offset={offset}"
        path: str = f"{self.indexed_files}/{filter}"
        response: Response = get(self.beta_url, path=path, headers=self.user.authentication_header)
        assert response.status_code == requests.codes.ok, response.content
        csp_indexed_files: CSPIndexedFilesAndFoldersSystemInfoList = CSPIndexedFilesAndFoldersSystemInfoList.from_json(
            response.text
        )
        return csp_indexed_files.to_domain_model()

    # INTERNAL API to delete Index-File data for a given Backup
    # https://github.hpe.com/nimble-dcs/hybridcloud-file-index-search#internal-delete-api
    #
    # DELETE /test/v1/nb-rest.fiss/indexed-files
    def delete_indexed_files_for_backup(
        self,
        csp_asset_type: CSPResourceType,
        csp_asset_id: str,
        csp_backup_id: str,
    ):
        logger.info(
            f"calling delete indexed-files endpoint: asset_type: {csp_asset_type.value}, asset_id: {csp_asset_id}, backup_id: {csp_backup_id}"
        )
        url = self.dscc["atlantia-url"]
        # No GLCP changes for the test url.
        path = f"test/v1/nb-rest.fiss/indexed-files?asset-type={csp_asset_type.value}&asset-id={csp_asset_id}&backup-id={csp_backup_id}"
        response: Response = delete(url, path, headers=self.user.authentication_header)
        # There is no "task_id" returned for this Internal Call - much like "copy2cloud".
        # we'll need to look for the Task by name and wait for it to complete
        #
        # response.status_code == 404 if there is no Index-Files found for the Backup
        if response.status_code == requests.codes.ok:
            logger.info("delete Indexed-Files for Backup started")
        else:
            logger.info("No Indexed-Files found for Backup")
