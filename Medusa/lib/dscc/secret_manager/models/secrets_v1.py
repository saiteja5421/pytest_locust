import datetime
from dataclasses import dataclass

from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.secret_manager.common.models.common_secret_objects import (
    ObjectNameUriId,
    Domain,
    Subclassifier,
)
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import ObjectName
from lib.dscc.secret_manager.models.domain_model.secrets_model import SecretListModel, SecretModel


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
# NOTE# label attribute given in the spec but not in application response
class Secret:
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
    domain: Domain
    classifier: ObjectName
    subclassifier: Subclassifier
    status: str
    status_updated_at: datetime
    assignments_count: int

    def to_domain_model(self):
        return SecretModel(
            customer_id=self.customer_id,
            service=self.service,
            id=self.id,
            name=self.name,
            type=self.type,
            resource_uri=self.resource_uri,
            updated_at=self.updated_at,
            created_at=self.created_at,
            groups=self.groups,
            domain=self.domain,
            classifier=self.classifier,
            subclassifier=self.subclassifier,
            status=self.status,
            status_updated_at=self.status_updated_at,
            assignments_count=self.assignments_count,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SecretList:
    items: list[Secret]
    page_limit: int
    page_offset: int
    total: int

    def to_domain_model(self):
        return SecretListModel(
            items=[item.to_domain_model() for item in self.items],
            page_limit=self.page_limit,
            page_offset=self.page_offset,
            total=self.total,
        )
