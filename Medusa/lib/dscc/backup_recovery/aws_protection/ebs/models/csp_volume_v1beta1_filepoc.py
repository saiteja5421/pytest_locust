from typing import Union
import datetime
from dataclasses import dataclass
import json

from dataclasses_json import dataclass_json, LetterCase
from lib.common.enums.csp_type import CspType
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    AttachmentInfo,
    ObjectCountType,
    CspProtectionJobInfo,
    CSPTag,
    ObjectNameResourceTypeId,
    ObjectReferenceWithId,
)
from lib.dscc.backup_recovery.aws_protection.ebs.domain_models.csp_volume_model import (
    CSPVolumeListModel,
    CSPVolumeModel,
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


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AzureDiskCSPInfo:
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
    cspInfo: Union[EBSCSPInfo, AzureDiskCSPInfo]
    cspName: str
    cspType: str
    machineInstanceAttachmentInfo: list[AttachmentInfo]
    state: str
    protectionGroupInfo: list[ObjectNameResourceTypeId]
    protectionJobInfo: list[CspProtectionJobInfo]
    protectionStatus: str
    subscriptionInfo: ObjectNameResourceTypeId
    consoleUri: str = None

    def __init__(self, **kwargs):
        cspType: str = kwargs["cspType"]
        for key, value in kwargs.items():
            if key == "cspInfo" and cspType == CspType.AWS.value:
                self.cspInfo = EBSCSPInfo.from_json(json.dumps(value))
            elif key == "cspInfo" and cspType == CspType.AZURE.value:
                self.cspInfo = AzureDiskCSPInfo.from_json(json.dumps(value))
            else:
                super().__setattr__(key, value)

    def to_domain_model(self):
        return CSPVolumeModel(
            customerId=self.customerId,
            generation=self.generation,
            id=self.id,
            name=self.name,
            resourceUri=self.resourceUri,
            type=self.type,
            accountInfo=self.accountInfo,
            backupInfo=self.backupInfo,
            cspId=self.cspId,
            cspInfo=self.cspInfo,
            cspName=self.cspName,
            cspType=self.cspType,
            machineInstanceAttachmentInfo=self.machineInstanceAttachmentInfo,
            state=self.state,
            protectionGroupInfo=self.protectionGroupInfo,
            protectionJobInfo=self.protectionJobInfo,
            protectionStatus=self.protectionStatus,
            consoleUri=self.consoleUri,
            subscriptionInfo=self.subscriptionInfo,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPVolumeList:
    items: list[CSPVolume]
    count: int
    offset: int
    total: int

    def to_domain_model(self):
        return CSPVolumeListModel(
            items=[item.to_domain_model() for item in self.items],
            count=self.count,
            offset=self.offset,
            total=self.total,
        )
