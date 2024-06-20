from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PatchSettings:
    current_value: str  # Value must be "ON" or "OFF"
