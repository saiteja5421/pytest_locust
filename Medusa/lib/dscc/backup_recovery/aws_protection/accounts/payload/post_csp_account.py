from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PostCSPAccount:
    csp_id: str
    name: str
    csp_type: str = "AWS"
