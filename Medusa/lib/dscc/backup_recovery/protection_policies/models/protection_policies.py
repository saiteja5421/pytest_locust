from typing import List, Optional
from uuid import UUID

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    ObjectId,
    ObjectIdName,
    ObjectUnitValue,
    CopyPoolInfo,
    NamePattern,
    Schedule,
    PreScriptInfo,
    PostScriptInfo,
)
from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase
from lib.common.enums.object_unit_type import ObjectUnitType

# https://pages.github.hpe.com/cloud/storage-api/api-v1-index.html#get-/protection-policies


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
    id: Optional[int] = field(default=None)
    post_script_info: Optional[PostScriptInfo] = field(default=None)
    pre_script_info: Optional[PreScriptInfo] = field(default=None)


# PolicyProtections
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class PolicyProtection:
    id: UUID
    schedules: list[PolicySchedule]
    type: str = None
    application_type: str = None
    copy_pool_info: Optional[CopyPoolInfo] = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionPolicy:
    assigned: bool
    id: str
    name: str
    protections: list[PolicyProtection]
    created_at: str
    created_by: ObjectIdName
    generation: int
    resource_uri: str
    type: str
    updated_at: str
    console_uri: str = field(default="")
    policy_type: str = field(default="")
    description: str = field(default="")
    protection_jobs_info: list[ObjectId] = field(default_factory=lambda: [])


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionPolicyList:
    items: List[ProtectionPolicy]
    page_limit: int
    page_offset: int
    total: int


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Schedules:
    id: int
    schedule: Schedule
    expire_after: ObjectUnitValue = field(default_factory=ObjectUnitValue(ObjectUnitType.HOURS.value, 0))
    lock_for: ObjectUnitValue = field(default_factory=ObjectUnitValue(ObjectUnitType.HOURS.value, 0))
    name_pattern: NamePattern = field(default_factory=NamePattern("Test_{SourceAssetName}_Copy_{DateFormat}"))
    name: str = "Hourly snapshot schedule"
    source_protection_schedule_id: int = 0
    verify: bool = False


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Protection:
    copyPoolId: UUID
    schedules: list[Schedules]
    type: str = "Snapshot"
