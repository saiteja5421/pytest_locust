from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PsgwSizePayload:
    max_in_cloud_daily_protected_data_in_tiB: float
    max_in_cloud_retention_days: int
    max_on_prem_daily_protected_data_in_tiB: float
    max_on_prem_retention_days: int
