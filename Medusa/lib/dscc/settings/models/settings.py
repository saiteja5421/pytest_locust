from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.settings.models.settings_info import SettingsInfo


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Settings:
    console_uri: str
    current_value: str
    customer_id: str
    description: str
    external_application_name: str
    generation: int
    id: str
    last_updated_at: str
    last_updated_by: str
    name: str
    next_value: str
    # TODO: Need to confirm this, if it should be represented as string or as list
    possible_values: list[SettingsInfo]
    resource_uri: str
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SettingsList:
    items: list[Settings]
    page_limit: int
    page_offset: int
    total: int
