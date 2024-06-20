from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase
import datetime
from typing import Optional
from uuid import UUID
from lib.common.enums.app_type import AppType

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ObjectIdName,
    ObjectId,
    ObjectUnitValue,
    NamePattern,
    Schedule,
    PostScriptInfo,
    PreScriptInfo,
)

# https://pages.github.hpe.com/cloud/storage-api/backup-recovery/v1beta1/index.html#tag/protection-policies


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PolicySchedule:
    schedule: Schedule
    name_pattern: Optional[NamePattern] = field(default=None)
    name: Optional[str] = field(default=None)
    expire_after: Optional[ObjectUnitValue] = field(default=None)
    verify: bool = field(default=None)
    source_protection_schedule_id: Optional[int] = field(default=None)
    lock_for: Optional[ObjectUnitValue] = field(default=None)
    post_script_info: Optional[PostScriptInfo] = field(default=None)
    pre_script_info: Optional[PreScriptInfo] = field(default=None)
    schedule_id: Optional[int] = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CopyPoolInfo:
    id: UUID
    name: str
    protection_store_type: str
    resource_uri: str
    type: str


# PolicyProtections
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PolicyProtection:
    id: UUID
    schedules: list[PolicySchedule]
    type: str = None
    protection_store_info: Optional[CopyPoolInfo] = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionPolicy:
    assigned: bool
    id: str
    name: str
    protections: list[PolicyProtection]
    created_at: datetime
    created_by: ObjectIdName
    generation: int
    resource_uri: str
    type: str
    updated_at: datetime
    console_uri: str = field(default="")
    description: str = field(default="")
    protection_jobs_info: list[ObjectId] = field(default_factory=lambda: [])
    application_type: Optional[AppType] = field(default=None)


# NOTE: The v1beta1 endpoint continues to return v1 ProtectionPolicyList fields
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionPolicyList:
    items: list[ProtectionPolicy]
    page_limit: int
    page_offset: int
    total: int
