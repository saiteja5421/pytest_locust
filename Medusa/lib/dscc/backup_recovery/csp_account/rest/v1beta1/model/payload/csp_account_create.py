from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from lib.common.enums.csp_type import CspType


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPAccountCreate:
    csp_id: str
    csp_type: CspType
    name: str
