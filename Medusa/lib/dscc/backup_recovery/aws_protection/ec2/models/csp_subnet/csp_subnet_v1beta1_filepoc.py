import json
from dataclasses import dataclass
from uuid import UUID
from typing import Union
from dataclasses_json import dataclass_json, LetterCase
from lib.common.enums.csp_type import CspType
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import ObjectReferenceWithId
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_subnet_model import (
    CSPSubnetListModel,
    CSPSubnetModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPSubnetAwsInfo:
    availabilityZone: str
    cspRegion: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPSubnetAzureInfo:
    cspRegion: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPSubnet:
    account_info: ObjectReferenceWithId
    csp_id: str
    csp_info: Union[CSPSubnetAwsInfo, CSPSubnetAzureInfo]
    csp_name: str
    csp_type: str
    customer_id: str
    generation: int
    id: UUID
    name: str
    resource_uri: str
    type: str
    vpc_info: ObjectReferenceWithId

    def __init__(self, **kwargs):
        cspType: str = kwargs["csp_type"]
        for key, value in kwargs.items():
            if key == "cspInfo" and cspType == CspType.AWS.value:
                self.cspInfo = CSPSubnetAwsInfo.from_json(json.dumps(value))
            elif key == "cspInfo" and cspType == CspType.AZURE.value:
                self.cspInfo = CSPSubnetAzureInfo.from_json(json.dumps(value))
            else:
                super().__setattr__(key, value)

    def to_domain_model(self):
        return CSPSubnetModel(
            account_info=self.account_info,
            csp_id=self.csp_id,
            csp_info=self.csp_info,
            csp_name=self.csp_name,
            csp_type=self.csp_type,
            customer_id=self.customer_id,
            generation=self.generation,
            id=self.id,
            name=self.name,
            resource_uri=self.resource_uri,
            type=self.type,
            vpc_info=self.vpc_info,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPSubnetList:
    items: list[CSPSubnet]
    count: int

    def to_domain_model(self):
        return CSPSubnetListModel(items=[item.to_domain_model() for item in self.items], count=self.count)
