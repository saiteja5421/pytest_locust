from dataclasses import dataclass, field
from typing import Optional, cast
from uuid import UUID
from dataclasses_json import dataclass_json, LetterCase, config
from datetime import datetime
from lib.common.enums.app_type import AppType
from lib.common.enums.protection_types import ProtectionType
from lib.common.enums.object_unit_type import ObjectUnitType
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import ObjectUnitValue, Schedule, NamePattern

SENTINEL = cast(object, None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Schedules:
    scheduleId: int
    schedule: Schedule
    expire_after: ObjectUnitValue = field(default_factory=ObjectUnitValue(ObjectUnitType.HOURS.value, 1))
    lock_for: ObjectUnitValue = field(default_factory=ObjectUnitValue(ObjectUnitType.HOURS.value, 0))
    name_pattern: NamePattern = field(default_factory=NamePattern("Test_{SourceAssetName}_Copy_{DateFormat}"))
    name: str = "Hourly snapshot schedule"
    sourceProtectionScheduleId: Optional[str] = field(
        default=SENTINEL, metadata=config(exclude=lambda x: x is SENTINEL)
    )
    verify: bool = field(default=None)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Protection:
    schedules: list[Schedules]
    type: Optional[ProtectionType] = field(default=SENTINEL, metadata=config(exclude=lambda x: x is SENTINEL))
    copyPoolId: Optional[UUID] = field(default=SENTINEL, metadata=config(exclude=lambda x: x is SENTINEL))


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class Protections:
    protections: list[Protection]
    name: str = f"Protection-policy-{datetime.now().strftime('%D %H:%M:%S')}"
    description: str = "Protection Policy created by Medusa framework"
    applicationType: Optional[AppType] = field(default=SENTINEL, metadata=config(exclude=lambda x: x is SENTINEL))
