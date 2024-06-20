from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from uuid import UUID
from lib.dscc.backup_recovery.aws_protection.ec2.models.common import (
    ObjectReferenceWithId,
)
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_resource_group_model import (
    CSPResourceGroupListModel,
    CSPResourceGroupModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPResourceGroupAzureInfo:
    csp_region: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPResourceGroup:
    """
    CSP Resource Group class that represents the response from the Inventory Manager resource group API.
    """

    account_info: ObjectReferenceWithId
    csp_id: str
    csp_info: CSPResourceGroupAzureInfo
    csp_name: str
    csp_type: str
    customer_id: str
    generation: int
    id: UUID
    name: str
    resource_uri: str
    subscription_info: ObjectReferenceWithId
    type: str

    def to_domain_model(self):
        return CSPResourceGroupModel(
            account_info=self.account_info,
            csp_id=self.csp_id,
            csp_name=self.csp_name,
            customer_id=self.customer_id,
            generation=self.generation,
            id=self.id,
            name=self.name,
            resource_uri=self.resource_uri,
            subscription_info=self.subscription_info,
            type=self.type,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPResourceGroupList:
    """
    CSP Resource Group List class that represents the response from the Inventory Manager resource group API.
    """

    items: list[CSPResourceGroup]
    count: int

    def to_domain_model(self):
        return CSPResourceGroupListModel(items=[item.to_domain_model() for item in self.items], count=self.count)
