from datetime import datetime
from uuid import UUID

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    AssetInfo,
    CopyPoolInfo,
    NamePattern,
    ObjectUnitValue,
    Schedule,
)

from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase
from typing import Optional

# https://pages.github.hpe.com/cloud/storage-api/api-v1-index.html#get-/protection-jobs


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionPolicyInfo:
    id: str
    name: str
    resourceUri: Optional[str] = field(default=None)
    type: Optional[str] = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ExecutionStatus:
    status: str
    taskUri: str
    timestamp: datetime
    errorMessage: Optional[str] = field(default="")


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ActiveTime:
    active_from_time: str
    active_until_time: str


@dataclass
class RepeatInterval:
    every: int
    on: list[int]


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Overrides:
    backup_granularity: str
    consistency: str
    expire_after: ObjectUnitValue
    lock_for: ObjectUnitValue
    name: str
    name_pattern: NamePattern
    schedule: Schedule
    verify: bool


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VMWareOptions:
    includeRdmDisks: bool


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionSchedule:
    execution_statuses: list[ExecutionStatus]
    id: int
    next_run_time: datetime
    operational: str
    prev_run_time: datetime
    prev_successful_run_time: datetime
    vmware_options: VMWareOptions
    overrides: Optional[Overrides]
    expire_after: ObjectUnitValue
    name_pattern: NamePattern
    schedule: Schedule
    lock_for: ObjectUnitValue


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Protection:
    copy_pool_info: CopyPoolInfo
    id: UUID
    schedules: list[ProtectionSchedule]
    type: str
    applicationType: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionJob:
    asset_info: AssetInfo
    effective_from_date_time: str
    generation: int
    id: UUID
    on_prem_engine_id: UUID
    operational: str
    protections: list[Protection]
    resource_uri: str
    type: str
    protection_policy_info: ProtectionPolicyInfo


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionJobList:
    items: list[ProtectionJob]
    page_limit: int
    page_offset: int
    total: int
