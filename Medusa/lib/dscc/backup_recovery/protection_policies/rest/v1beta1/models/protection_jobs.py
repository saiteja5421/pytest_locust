from uuid import UUID

from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    AssetInfo,
    NamePattern,
    ObjectUnitValue,
    Schedule,
)
from lib.dscc.backup_recovery.protection_policies.rest.v1beta1.models.protection_policies import CopyPoolInfo

from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, LetterCase
from typing import Optional
from lib.common.enums.app_type import AppType

# https://pages.github.hpe.com/cloud/storage-api/backup-recovery/v1beta1/index.html#tag/protection-jobs


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionPolicyInfo:
    id: UUID
    name: str
    resourceUri: Optional[str] = field(default=None)
    type: Optional[str] = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ExecutionStatus:
    status: str
    taskUri: str
    timestamp: str
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
    expire_after: ObjectUnitValue
    name: str
    name_pattern: NamePattern
    schedule: Schedule
    backup_granularity: Optional[str] = field(default=None)
    verify: Optional[bool] = field(default=None)
    lock_for: Optional[ObjectUnitValue] = field(default=None)
    consistency: Optional[str] = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class VMWareOptions:
    include_rdm_disks: bool


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionSchedule:
    schedule_id: int
    operational: Optional[str] = field(default=None)
    expire_after: Optional[ObjectUnitValue] = field(default=None)
    name_pattern: Optional[NamePattern] = field(default=None)
    schedule: Optional[Schedule] = field(default=None)
    name: Optional[str] = field(default=None)
    source_protection_schedule_id: Optional[int] = field(default=None)
    verify: Optional[bool] = field(default=None)
    execution_statuses: Optional[list[ExecutionStatus]] = field(default_factory=lambda: [])
    next_run_time: Optional[str] = field(default=None)
    prev_run_time: Optional[str] = field(default=None)
    prev_successful_run_time: Optional[str] = field(default=None)
    vmware_options: Optional[VMWareOptions] = field(default=None)
    lock_for: Optional[ObjectUnitValue] = field(default=None)
    overrides: Optional[Overrides] = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Protection:
    id: UUID
    schedules: list[ProtectionSchedule]
    type: str
    protection_store_info: Optional[CopyPoolInfo] = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionJob:
    asset_info: AssetInfo
    generation: int
    id: UUID
    resource_uri: str
    protections: Optional[list[Protection]] = field(default_factory=lambda: [])
    type: Optional[str] = field(default=None)
    effective_from_date_time: Optional[str] = field(default=None)
    on_prem_engine_id: Optional[UUID] = field(default=None)
    operational: Optional[str] = field(default=None)
    protection_policy_info: Optional[ProtectionPolicyInfo] = field(default=None)
    application_type: Optional[AppType] = field(default=None)


# NOTE: The v1beta1 endpoint continues to return v1 ProtectionJobList fields
@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionJobList:
    items: list[ProtectionJob]
    page_limit: int
    page_offset: int
    total: int
