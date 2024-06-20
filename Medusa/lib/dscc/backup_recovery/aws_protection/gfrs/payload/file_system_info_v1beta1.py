"""
API Specifications:
https://pages.github.hpe.com/cloud/storage-api/backup-recovery/v1beta1/#tag/Granular-File-Level-Recovery
"""

from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase

from lib.dscc.backup_recovery.aws_protection.gfrs.domain_models.gfrs_models import (
    PostCSPFileSystemInfoModel,
    PostRestoreCSPFileSystemInfoModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostCSPFileSystemInfo:
    absolute_source_path: str
    file_system_id: str

    @staticmethod
    def from_domain_model(domain_model: PostCSPFileSystemInfoModel):
        return PostCSPFileSystemInfo(
            absolute_source_path=domain_model.absolute_source_path, file_system_id=domain_model.file_system_id
        )

    def to_domain_model(self):
        return PostCSPFileSystemInfoModel(
            absolute_source_path=self.absolute_source_path,
            file_system_id=self.file_system_id,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostRestoreCSPFileSystemInfo:
    restore_info: list[PostCSPFileSystemInfo]

    @staticmethod
    def from_domain_model(domain_model: PostRestoreCSPFileSystemInfoModel):
        return PostRestoreCSPFileSystemInfo(
            restore_info=[PostCSPFileSystemInfo.from_domain_model(info) for info in domain_model.restore_info]
        )

    def to_domain_model(self):
        return PostRestoreCSPFileSystemInfoModel(restore_info=[info.to_domain_model() for info in self.restore_info])
