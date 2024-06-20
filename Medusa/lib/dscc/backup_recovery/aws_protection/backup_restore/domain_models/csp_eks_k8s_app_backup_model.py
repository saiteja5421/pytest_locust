from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from dataclasses_json import LetterCase, dataclass_json


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sAppBackupInfoModel:
    id: UUID
    state: str
    status: str
    backup_type: str
    expires_at: Optional[str] = None
    locked_until: Optional[str] = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPK8sAppBackupListModel:
    total: int
    items: list[CSPK8sAppBackupInfoModel]
