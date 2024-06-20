"""
API Specifications:
https://pages.github.hpe.com/cloud/storage-api/backup-recovery/v1beta1/#tag/Granular-File-Level-Recovery
"""

from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase, config

from lib.dscc.backup_recovery.aws_protection.gfrs.domain_models.csp_indexed_file_system_info_model import (
    CSPIndexedFileSystemInfoModel,
    CSPIndexedFileSystemInfoListModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPIndexedFileSystemInfo:
    drive_name: str
    filesystem_type: str
    id: str
    mount_path: str
    os_partition_id: str
    total_size_in_bytes: int
    # because 'type' is a reserved word
    type_: str = field(metadata=config(field_name="type"))
    used_size_in_bytes: int
    # v1beta1 does not have the following 2 fields. Present in v1beta2 (FLR V2)
    indexing_error: bool = False
    mount_id: str = ""

    def to_domain_model(self):
        return CSPIndexedFileSystemInfoModel(
            drive_name=self.drive_name,
            filesystem_type=self.filesystem_type,
            id=self.id,
            mount_path=self.mount_path,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPIndexedFileSystemInfoList:
    items: list[CSPIndexedFileSystemInfo]
    count: int

    def to_domain_model(self):
        return CSPIndexedFileSystemInfoListModel(
            items=[item.to_domain_model() for item in self.items], count=self.count
        )
