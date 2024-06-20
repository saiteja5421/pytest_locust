from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class LocationModel:
    location: str
    task_id: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostCSPFileSystemInfoModel:
    absolute_source_path: str
    file_system_id: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostRestoreCSPFileSystemInfoModel:
    restore_info: list[PostCSPFileSystemInfoModel]
