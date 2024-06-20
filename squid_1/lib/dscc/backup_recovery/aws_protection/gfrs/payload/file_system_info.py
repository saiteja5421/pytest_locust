"""
API Specifications:
https://pages.github.hpe.com/cloud/storage-api/backup-recovery/v1beta1/#tag/Granular-File-Level-Recovery
"""

from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostCSPFileSystemInfo:
    absolute_source_path: str
    file_system_id: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostRestoreCSPFileSystemInfo:
    restore_info: list[PostCSPFileSystemInfo]
