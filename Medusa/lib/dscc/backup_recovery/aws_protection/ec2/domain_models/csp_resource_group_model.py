from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from uuid import UUID
from lib.dscc.backup_recovery.aws_protection.ec2.models.common import (
    ObjectReferenceWithId,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPResourceGroupAzureInfoModel:
    csp_region: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPResourceGroupModel:
    """
    CSP Resource Group class that represents the response from the Inventory Manager resource group API.
    """

    account_info: ObjectReferenceWithId
    csp_id: str
    csp_info: CSPResourceGroupAzureInfoModel
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
class CSPResourceGroupListModel:
    """
    CSP Resource Group List class that represents the response from the Inventory Manager resource group API.
    """

    items: list[CSPResourceGroupModel]
    count: int
