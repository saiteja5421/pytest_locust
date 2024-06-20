"""
API Specifications:
https://pages.github.hpe.com/cloud/storage-api/backup-recovery/v1beta1/#tag/Granular-File-Level-Recovery
"""

from dataclasses import dataclass, field
import datetime
from dataclasses_json import dataclass_json, LetterCase, config

from lib.dscc.backup_recovery.aws_protection.gfrs.domain_models.csp_indexed_files_and_folders_info_model import (
    CSPIndexedFilesAndFoldersSystemInfoModel,
    CSPIndexedFilesAndFoldersSystemInfoListModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPIndexedFilesAndFoldersSystemInfo:
    absolute_path: str
    file_type: str
    id: str
    last_modified_time: datetime
    name: str
    size_in_bytes: int
    type_: str = field(metadata=config(field_name="type"))
    # v1beta2 has the following 2 fields
    file_mode: int = 0
    index_status: str = ""

    def to_domain_model(self):
        return CSPIndexedFilesAndFoldersSystemInfoModel(id=self.id, name=self.name)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPIndexedFilesAndFoldersSystemInfoList:
    count: int
    items: list[CSPIndexedFilesAndFoldersSystemInfo]
    offset: int
    total: int
    # v1beta1 has "rootPath" field
    root_path: str = ""

    def to_domain_model(self):
        return CSPIndexedFilesAndFoldersSystemInfoListModel(
            items=[item.to_domain_model() for item in self.items],
            count=self.count,
            offset=self.offset,
            total=self.total,
        )
