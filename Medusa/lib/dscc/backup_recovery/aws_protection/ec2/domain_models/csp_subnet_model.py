from dataclasses import dataclass
from uuid import UUID
from typing import Union
from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import ObjectReferenceWithId


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPSubnetAwsInfoModel:
    availability_zone: str
    csp_region: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPSubnetAzureInfoModel:
    csp_region: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPSubnetModel:
    account_info: ObjectReferenceWithId
    csp_id: str
    csp_info: Union[CSPSubnetAwsInfoModel, CSPSubnetAzureInfoModel]
    csp_name: str
    csp_type: str
    customer_id: str
    generation: int
    id: UUID
    name: str
    resource_uri: str
    type: str
    vpc_info: ObjectReferenceWithId


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPSubnetListModel:
    items: list[CSPSubnetModel]
    count: int
