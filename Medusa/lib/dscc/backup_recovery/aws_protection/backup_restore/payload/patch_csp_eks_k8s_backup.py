from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase
from typing import Optional


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PatchCSPK8sAppBackup:
    description: Optional[str] = field(default=None)
    expires_at: Optional[str] = field(default=None)
    name: Optional[str] = field(default=None)
