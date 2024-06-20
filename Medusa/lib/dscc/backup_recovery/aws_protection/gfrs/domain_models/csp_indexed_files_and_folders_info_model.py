from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPIndexedFilesAndFoldersSystemInfoModel:
    id: str
    name: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPIndexedFilesAndFoldersSystemInfoListModel:
    count: int
    items: list[CSPIndexedFilesAndFoldersSystemInfoModel]
    offset: int
    total: int
