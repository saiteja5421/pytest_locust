from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from uuid import UUID


@dataclass
class AssociatedResource:
    id: UUID
    name: str
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AuditEvent:
    associatedResource: AssociatedResource
    code: str
    contextId: str
    customerId: str
    id: str
    loggedAt: str
    message: str
    occurredAt: str
    permission: str
    scope: str
    source: str
    sourceIpAddress: str
    state: str
    taskId: str
    uniqueId: str
    userEmail: str
    version: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AuditEventList:
    items: list[AuditEvent]
    pageLimit: int
    pageOffset: int
    total: int
