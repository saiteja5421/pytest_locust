"""
API Specifications:
https://pages.github.hpe.com/cloud/storage-api/backup-recovery/v1beta1/#tag/Granular-File-Level-Recovery
"""

from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase, config


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPIndexedFileSystemInfo:
    drive_name: str
    filesystem_type: str
    id: str
    indexing_error: bool
    mount_id: str
    mount_path: str
    os_partition_id: str
    total_size_in_bytes: int
    # because 'type' is a reserved word
    type_: str = field(metadata=config(field_name="type"))
    used_size_in_bytes: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPIndexedFileSystemInfoList:
    items: list[CSPIndexedFileSystemInfo]
    count: int
