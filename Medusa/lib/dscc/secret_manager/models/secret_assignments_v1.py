import datetime
from dataclasses import dataclass

from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.secret_manager.common.models.common_secret_objects import ObjectNameUriId

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ObjectNameResourceTypeId,
    ObjectId,
)
from lib.dscc.secret_manager.models.domain_model.secret_assignments_model import (
    SecretAgreementsListModel,
    SecretAssignmentsModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
# NOTE# label attribute given in the spec but not in application response
class SecretAssignments:
    customer_id: str
    service: str
    id: str
    name: str
    type: str
    resource_uri: str
    generation: int
    updated_at: datetime
    created_at: datetime
    groups: list[ObjectNameUriId]
    status: str
    status_updated_at: datetime
    goal: str
    goal_updated_at: datetime
    secret: ObjectNameResourceTypeId
    appliance: ObjectId

    def to_domain_model(self):
        return SecretAssignmentsModel(
            customer_id=self.customer_id,
            service=self.service,
            id=self.id,
            name=self.name,
            type=self.type,
            resource_uri=self.resource_uri,
            generation=self.generation,
            updated_at=self.updated_at,
            created_at=self.created_at,
            groups=self.groups,
            status=self.status,
            status_updated_at=self.status_updated_at,
            goal=self.goal,
            goal_updated_at=self.goal_updated_at,
            secret=self.secret,
            appliance=self.appliance,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SecretAgreementsList:
    items: list[SecretAssignments]
    page_limit: int
    page_offset: int
    total: int

    def to_domain_model(self):
        return SecretAgreementsListModel(
            items=[item.to_domain_model() for item in self.items],
            page_limit=self.page_limit,
            page_offset=self.page_offset,
            total=self.total,
        )
