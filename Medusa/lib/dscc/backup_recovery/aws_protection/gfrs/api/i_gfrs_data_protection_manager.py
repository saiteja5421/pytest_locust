from typing import Protocol, Union, runtime_checkable

import requests

from lib.dscc.backup_recovery.aws_protection.gfrs.domain_models.gfrs_models import (
    LocationModel,
    PostRestoreCSPFileSystemInfoModel,
)
from lib.dscc.backup_recovery.aws_protection.gfrs.models.gfrs_error_response import GFRSErrorResponse


@runtime_checkable
class IGFRSDataProtectionManager(Protocol):
    def restore_csp_machine_instance_files_folders(
        self,
        csp_backup_id: str,
        restore_info: PostRestoreCSPFileSystemInfoModel,
        response_code=requests.codes.accepted,
    ) -> Union[LocationModel, GFRSErrorResponse]: ...

    def restore_csp_volume_files_folders(
        self,
        csp_backup_id: str,
        restore_info: PostRestoreCSPFileSystemInfoModel,
        response_code=requests.codes.accepted,
    ) -> Union[LocationModel, GFRSErrorResponse]: ...
