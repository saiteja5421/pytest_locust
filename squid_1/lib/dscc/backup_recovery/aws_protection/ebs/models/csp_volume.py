import datetime
from dataclasses import dataclass

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
class EBSCSPInfo:
    availabilityZone: str
    createdAt: datetime
    isEncrypted: bool
    cspRegion: str
    sizeInGiB: int
    iops: int
    cspTags: list[CSPTag]
    volumeType: str

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, EBSCSPInfo)
            and (self.availabilityZone == other.availabilityZone)
            and (self.createdAt == other.createdAt)
            and (self.isEncrypted == other.isEncrypted)
            and (self.cspRegion == other.cspRegion)
            and (self.sizeInGiB == other.sizeInGiB)
            and (self.iops == other.iops)
            and (len(self.cspTags) == len(other.cspTags))
            and {x.to_json() for x in self.cspTags} == {x.to_json() for x in other.cspTags}
            and (self.volumeType == other.volumeType)
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPVolume:
    customerId: str
    generation: int
    id: str
    name: str
    resourceUri: str
    type: str
    accountInfo: ObjectReferenceWithId
    backupInfo: list[ObjectCountType]
    cspId: str
    cspInfo: EBSCSPInfo
    cspName: str
    cspType: str
    machineInstanceAttachmentInfo: list[AttachmentInfo]
    state: str
    protectionGroupInfo: list[ObjectNameResourceTypeId]
    protectionJobInfo: list[CspProtectionJobInfo]
    protectionStatus: str
    consoleUri: str = None

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, CSPVolume)
            and (self.customerId == other.customerId)
            and (self.generation == other.generation)
            and (self.id == other.id)
            and (self.name == other.name)
            and (self.resourceUri == other.resourceUri)
            and (self.type == other.type)
            and (self.accountInfo == other.accountInfo)
            and (len(self.backupInfo) == len(other.backupInfo))
            and {x.to_json() for x in self.backupInfo} == {x.to_json() for x in other.backupInfo}
            and (self.cspInfo == other.cspInfo)
            and (self.cspId == other.cspId)
            and (self.cspName == other.cspName)
            and (self.cspType == other.cspType)
            and (len(self.machineInstanceAttachmentInfo) == len(other.machineInstanceAttachmentInfo))
            and {x.to_json() for x in self.machineInstanceAttachmentInfo}
            == {x.to_json() for x in other.machineInstanceAttachmentInfo}
            and (self.state == other.state)
            and (len(self.protectionGroupInfo) == len(other.protectionGroupInfo))
            and {x.to_json() for x in self.protectionGroupInfo} == {x.to_json() for x in other.protectionGroupInfo}
            and (len(self.protectionJobInfo) == len(other.protectionJobInfo))
            and {x.to_json() for x in self.protectionJobInfo} == {x.to_json() for x in other.protectionJobInfo}
            and (self.protectionStatus == other.protectionStatus)
            and (self.consoleUri == other.consoleUri)
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPVolumeList:
    items: list[CSPVolume]
    count: int
    offset: int
    total: int
