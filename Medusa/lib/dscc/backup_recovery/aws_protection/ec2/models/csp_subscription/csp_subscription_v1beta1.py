from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from uuid import UUID
from lib.dscc.backup_recovery.aws_protection.ec2.models.common import (
    ObjectReferenceWithId,
)
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_subscription_model import (
    CSPSubscriptionListModel,
    CSPSubscriptionModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPSubscription:
    """
    CSP Subscription class that represents the response from the Inventory Manager subscription API.
    """

    account_info: ObjectReferenceWithId
    csp_id: str
    csp_name: str
    csp_type: str
    customer_id: str
    generation: int
    id: UUID
    name: str
    resource_uri: str
    type: str

    def to_domain_model(self):
        return CSPSubscriptionModel(
            account_info=self.account_info,
            csp_id=self.csp_id,
            csp_name=self.csp_name,
            csp_type=self.csp_type,
            customer_id=self.customer_id,
            generation=self.generation,
            id=self.id,
            name=self.name,
            resource_uri=self.resource_uri,
            type=self.type,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPSubscriptionList:
    """
    CSP Subscription List class that represents the response from the Inventory Manager subscription API.
    """

    items: list[CSPSubscription]
    count: int

    def to_domain_model(self):
        return CSPSubscriptionListModel(items=[item.to_domain_model() for item in self.items], count=self.count)
