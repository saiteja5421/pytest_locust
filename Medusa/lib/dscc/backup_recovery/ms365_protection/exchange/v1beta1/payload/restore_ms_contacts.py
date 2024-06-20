from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.common import RestoreItem


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class RestoreMS365Contacts:
    destination_user_id: str
    contacts: list[RestoreItem] = field(default=None)
