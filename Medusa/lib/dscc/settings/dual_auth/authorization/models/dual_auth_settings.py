from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase

import datetime


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class DualAuthSettings:
    console_uri: str
    current_value: str
    customer_id: str
    description: str
    external_application_name: str
    generation: int
    id: int
    last_updated_at: datetime
    last_updated_by: datetime
    name: str
    next_value: str
    possible_values: str
    resource_uri: str
    type: str
