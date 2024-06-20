from typing import Any, Optional
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ErrorResponse,
    ObjectNameResourceType,
    ObjectNameResourceTypeId,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class LogMessage:
    message: str
    timestamp_at: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class SourceResource:
    name: str
    type: str
    resource_uri: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AssociatedResource:
    name: str
    type: str
    resource_uri: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Task:
    id: str
    name: str
    display_name: str
    recommendations: list[Any]
    user_id: str
    type: str
    generation: int
    resource_uri: str
    customer_id: str
    created_at: str
    updated_at: str
    health_status: str
    state: str
    progress_percent: int
    suggested_polling_interval_seconds: int
    estimated_running_duration_minutes: int
    services: list[str]
    associated_resources: list[AssociatedResource]
    log_messages: list[LogMessage]
    root_task: ObjectNameResourceTypeId
    child_tasks: list[ObjectNameResourceType]
    subtree_task_count: int
    started_at: Optional[str] = field(default=None)
    ended_at: Optional[str] = field(default=None)
    source_resource: Optional[SourceResource] = field(default=None)
    parent_task: Optional[ObjectNameResourceTypeId] = field(default=None)
    error: Optional[ErrorResponse] = field(default=None)
    additional_details: Optional[str] = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class TaskList:
    items: list[Task]
    page_limit: int
    page_offset: int
    total: int
