from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostRestoreCspRdsInstance:
    database_identifier: str  # Name of the restored RDS instance identifier
