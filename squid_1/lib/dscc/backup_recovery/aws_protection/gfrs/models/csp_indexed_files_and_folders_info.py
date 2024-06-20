"""
API Specifications:
https://pages.github.hpe.com/cloud/storage-api/backup-recovery/v1beta1/#tag/Granular-File-Level-Recovery
"""

from dataclasses import dataclass, field
import datetime
from dataclasses_json import dataclass_json, LetterCase, config


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPIndexedFilesAndFoldersSystemInfo:
    absolute_path: str
    file_mode: int
    file_type: str
    id: str
    index_status: str
    last_modified_time: datetime
    name: str
    size_in_bytes: int
    type_: str = field(metadata=config(field_name="type"))


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPIndexedFilesAndFoldersSystemInfoList:
    count: int
    items: list[CSPIndexedFilesAndFoldersSystemInfo]
    offset: int
    total: int
