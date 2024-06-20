from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import RefreshInfo


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPRDSAccountModel:
    customer_id: str
    id: str
    name: str
    resource_uri: str
    type: str
    refresh: RefreshInfo
