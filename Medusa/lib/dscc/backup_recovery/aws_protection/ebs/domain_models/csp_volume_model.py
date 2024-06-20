import datetime
from dataclasses import dataclass
from typing import Union

from dataclasses_json import dataclass_json, LetterCase
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    AttachmentInfo,
    ObjectCountType,
    CspProtectionJobInfo,
    CSPTag,
    ObjectNameResourceTypeId,
    ObjectReferenceWithId,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EBSCSPInfoModel:
    availabilityZone: str
    createdAt: datetime
    isEncrypted: bool
    cspRegion: str
    sizeInGiB: int
    iops: int
    cspTags: list[CSPTag]
    volumeType: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AzureDiskCSPInfoModel:
    availabilityZones: list[str]
    createdAt: datetime
    cspRegion: str
    cspTags: list[CSPTag]
    iops: int
    isEncrypted: bool
    sizeInGiB: int
    skuName: str
    uniqueId: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPVolumeModel:
    customerId: str
    generation: int
    id: str
    name: str
    resourceUri: str
    type: str
    accountInfo: ObjectReferenceWithId
    backupInfo: list[ObjectCountType]
    cspId: str
    cspInfo: Union[EBSCSPInfoModel, AzureDiskCSPInfoModel]
    cspName: str
    cspType: str
    machineInstanceAttachmentInfo: list[AttachmentInfo]
    state: str
    protectionGroupInfo: list[ObjectNameResourceTypeId]
    protectionJobInfo: list[CspProtectionJobInfo]
    protectionStatus: str
    subscriptionInfo: ObjectNameResourceTypeId
    consoleUri: str = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPVolumeListModel:
    items: list[CSPVolumeModel]
    count: int
    offset: int
    total: int
