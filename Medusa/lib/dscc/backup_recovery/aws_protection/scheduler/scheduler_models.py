from dataclasses import dataclass
from dataclasses_json import LetterCase, dataclass_json
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    AssetInfo,
    RepeatInterval,
    ObjectUnitValue,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionSchedule:
    id: int
    name: str
    consistency: str
    repeatInterval: RepeatInterval
    expireAfter: ObjectUnitValue
    lockFor: ObjectUnitValue
    recurrence: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionInfo:
    id: str
    type: str
    schedule: ProtectionSchedule


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class ProtectionPolicy:
    id: str
    name: str
    protection: ProtectionInfo


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class InitiateBackupRequest:
    id: str
    assetInfo: AssetInfo
    protectionPolicy: ProtectionPolicy


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class InitiateVpgBackupRequest:
    id: str
    assetInfo: AssetInfo
    protections: ProtectionInfo
    TaskID: str
