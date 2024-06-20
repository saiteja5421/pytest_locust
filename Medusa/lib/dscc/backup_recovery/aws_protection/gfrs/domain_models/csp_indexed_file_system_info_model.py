from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPIndexedFileSystemInfoModel:
    drive_name: str
    filesystem_type: str
    id: str
    mount_path: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPIndexedFileSystemInfoListModel:
    items: list[CSPIndexedFileSystemInfoModel]
    count: int
