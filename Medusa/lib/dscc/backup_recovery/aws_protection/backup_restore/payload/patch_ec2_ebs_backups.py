from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
# NOTE: name & description not included in PATCH API for release at the moment
class PatchEC2EBSBackups:
    # name: str
    # description: str
    expires_at: str
