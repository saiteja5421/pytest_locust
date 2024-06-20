from dataclasses import dataclass
from uuid import UUID
from typing import Union
from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import ObjectReferenceWithId


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPVpcAwsInfoModel:
    csp_region: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPVpcAzureInfoModel:
    csp_region: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPVPCModel:
    account_info: ObjectReferenceWithId
    csp_id: str
    csp_info: Union[CSPVpcAwsInfoModel, CSPVpcAzureInfoModel]
    csp_name: str
    csp_type: str
    customer_id: str
    generation: int
    id: UUID
    name: str
    resource_uri: str
    subscription_info: ObjectReferenceWithId
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPVPCListModel:
    items: list[CSPVPCModel]
    count: int
