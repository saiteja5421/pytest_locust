from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase

from lib.common.enums.dual_auth_request import DualAuthRequest, DualAuthSettingValue


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PatchRequestApproveDeny:
    checked_status: DualAuthRequest


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class UpdateDualAuthSetting:
    current_value: DualAuthSettingValue
