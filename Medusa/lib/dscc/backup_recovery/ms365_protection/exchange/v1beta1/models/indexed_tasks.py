import datetime
from uuid import UUID
from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.backup_recovery.ms365_protection.exchange.v1beta1.models.common import LinkedResource, Attachment
from lib.dscc.backup_recovery.ms365_protection.common.enums.importance import Importance
from lib.dscc.backup_recovery.ms365_protection.common.enums.status import TaskStatus


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class IndexedTask:
    attachments: list[Attachment]
    categories: list[str]
    checked_item_names: list[str]
    created_at: datetime
    folder_id: UUID
    folder_name: str
    id: UUID
    importance: Importance
    linked_resources: list[LinkedResource]
    task_status: TaskStatus
    title: str
    type: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class IndexedTaskList:
    items: list[IndexedTask]
    count: int
    offset: int
    total: int
