from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from uuid import UUID
from lib.dscc.backup_recovery.aws_protection.ec2.models.common import (
    ObjectReferenceWithId,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPSubscriptionModel:
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


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPSubscriptionListModel:
    """
    CSP Subscription List class that represents the response from the Inventory Manager subscription API.
    """

    items: list[CSPSubscriptionModel]
    count: int
