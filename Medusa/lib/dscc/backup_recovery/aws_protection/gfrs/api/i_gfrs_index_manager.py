"""
Class to make API calls to:
https://pages.github.hpe.com/cloud/storage-api/backup-recovery/v1beta1/#tag/Granular-File-Level-Recovery
APIs
"""

from typing import Protocol, Union, runtime_checkable
import requests

# domain models
from lib.dscc.backup_recovery.aws_protection.gfrs.domain_models.gfrs_models import PostCSPFileSystemInfoModel
from lib.dscc.backup_recovery.aws_protection.gfrs.domain_models.csp_indexed_file_system_info_model import (
    CSPIndexedFileSystemInfoListModel,
)
from lib.dscc.backup_recovery.aws_protection.gfrs.domain_models.csp_indexed_files_and_folders_info_model import (
    CSPIndexedFilesAndFoldersSystemInfoListModel,
)

from lib.dscc.backup_recovery.aws_protection.gfrs.models.gfrs_error_response import GFRSErrorResponse
from lib.common.enums.csp_resource_type import CSPResourceType


@runtime_checkable
class IGFRSIndexManager(Protocol):
    def index_guest_files_on_csp_volume_backup(
        self,
        csp_backup_id: str,
        post_file_system_info: PostCSPFileSystemInfoModel = "{}",
        response_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, GFRSErrorResponse]: ...

    def index_guest_files_on_csp_machine_instance_backup(
        self,
        csp_backup_id: str,
        post_file_system_info: PostCSPFileSystemInfoModel = "{}",
        response_code: requests.codes = requests.codes.accepted,
    ) -> Union[str, GFRSErrorResponse]: ...

    # GET /v1beta2/indexed-filesystems (FLR V2)
    # https://pages.github.hpe.com/cloud/storage-api/backup-recovery/v1beta2/#tag/Indexed-filesystems-for-granular-recovery/operation/FilesystemMetadataList
    def get_indexed_file_system_info_for_backup(
        self,
        csp_asset_type: CSPResourceType,
        csp_asset_id: str,
        csp_backup_id: str,
    ) -> CSPIndexedFileSystemInfoListModel: ...

    # GET /v1beta1/indexed-filesystems
    # https://pages.github.hpe.com/cloud/storage-api/backup-recovery/v1beta1/index.html#tag/indexed-filesystems/operation/IndexedFileSystemList
    def get_indexed_file_system_info_for_snapshot(
        self,
        csp_snapshot_id: str,
    ) -> CSPIndexedFileSystemInfoListModel: ...

    # GET /v1beta2/indexed-files (FLR V2)
    # https://pages.github.hpe.com/cloud/storage-api/backup-recovery/v1beta2/#tag/Indexed-files-for-granular-recovery/operation/FileMetadataList
    def get_files_and_folders_info_from_backup(
        self,
        csp_backup_id: str,
        offset: int = 0,
        limit: int = 1000,
    ) -> CSPIndexedFilesAndFoldersSystemInfoListModel: ...

    # GET /v1beta1/indexed-files
    # https://pages.github.hpe.com/cloud/storage-api/backup-recovery/v1beta1/index.html#tag/indexed-files/operation/IndexedFileList
    def get_files_and_folders_info_from_snapshot(
        self,
        csp_snapshot_id: str,
        root_path: str,
        offset: int = 0,
        limit: int = 1000,
    ) -> CSPIndexedFilesAndFoldersSystemInfoListModel: ...

    def delete_indexed_files_for_backup(
        self,
        csp_asset_type: CSPResourceType,
        csp_asset_id: str,
        csp_backup_id: str,
    ): ...
