from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Override:
    cpu: int
    ram_in_giB: int
    storage_in_tiB: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PsgwReSizePayload:
    max_in_cloud_daily_protected_data_in_tiB: float
    max_in_cloud_retention_days: int
    max_on_prem_daily_protected_data_in_tiB: float
    max_on_prem_retention_days: int
    override: Override = Override("cpu", "ram_in_giB", "storage_in_tiB")
    datastore_ids: list[str] = field(default_factory=list)
