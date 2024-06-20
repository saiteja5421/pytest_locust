import datetime
import json

from dataclasses import dataclass
from dataclasses_json import dataclass_json, LetterCase
from typing import Union
from lib.dscc.backup_recovery.aws_protection.common.models.common_objects import (
    AttachmentInfo,
    ObjectCountType,
    ObjectCspIdName,
    ObjectNameResourceTypeId,
    CspProtectionJobInfo,
    CSPTag,
    ObjectReferenceWithId,
)
from lib.common.enums.csp_type import CspType
from lib.dscc.backup_recovery.aws_protection.ec2.domain_models.csp_instance_model import (
    CSPMachineInstanceListModel,
    CSPMachineInstanceModel,
)


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class NetworkInfo:
    privateIpAddress: str
    publicIpAddress: str
    publicIpAddressIsFloating: bool
    securityGroups: list[ObjectCspIdName]
    subnetInfo: ObjectNameResourceTypeId
    vpcInfo: ObjectNameResourceTypeId


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EC2CSPInfo:
    accessProfileId: str
    availabilityZone: str
    cpuCoreCount: int
    createdAt: datetime
    instanceType: str
    keyPairName: str
    networkInfo: NetworkInfo
    platform: str
    cspRegion: str
    rootDevice: str
    state: str
    cspTags: list[CSPTag]
    virtualizationType: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class IpConfigurations:
    privateIpAddress: str
    publicIpAddress: str
    subnetInfo: ObjectNameResourceTypeId
    vpcInfo: ObjectNameResourceTypeId


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AzureNetworkInfo:
    connections: list[IpConfigurations]
    securityGroups: list[ObjectCspIdName]


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AzureCSPInfo:
    availabilityZones: list[str]
    cpuCoreCount: int
    createdAt: datetime
    instanceType: str
    keyPairName: str
    networkInfo: AzureNetworkInfo
    platform: str
    cspRegion: str
    rootDevice: str
    state: str
    cspTags: list[CSPTag]


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPMachineInstance:
    customerId: str
    generation: int
    id: str
    name: str
    resourceUri: str
    type: str
    accountInfo: ObjectReferenceWithId
    backupInfo: list[ObjectCountType]
    cspId: str
    cspInfo: Union[EC2CSPInfo, AzureCSPInfo]
    cspName: str
    cspType: str
    protectionGroupInfo: list[ObjectNameResourceTypeId]
    state: str
    volumeAttachmentInfo: list[AttachmentInfo]
    protectionJobInfo: list[CspProtectionJobInfo]
    protectionStatus: str
    subscriptionInfo: ObjectReferenceWithId
    consoleUri: str = None

    def __init__(self, **kwargs):
        cspType: str = kwargs["cspType"]
        for key, value in kwargs.items():
            if key == "cspInfo" and cspType == CspType.AWS.value:
                self.cspInfo = EC2CSPInfo.from_json(json.dumps(value))
            elif key == "cspInfo" and cspType == CspType.AZURE.value:
                self.cspInfo = AzureCSPInfo.from_json(json.dumps(value))
            else:
                super().__setattr__(key, value)

    def to_domain_model(self):
        return CSPMachineInstanceModel(
            id=self.id,
            name=self.name,
            customerId=self.customerId,
            generation=self.generation,
            resourceUri=self.resourceUri,
            type=self.type,
            cspId=self.cspId,
            accountInfo=self.accountInfo,
            backupInfo=self.backupInfo,
            cspInfo=self.cspInfo,
            cspName=self.cspName,
            cspType=self.cspType,
            protectionGroupInfo=self.protectionGroupInfo,
            state=self.state,
            volumeAttachmentInfo=self.volumeAttachmentInfo,
            protectionJobInfo=self.protectionJobInfo,
            protectionStatus=self.protectionStatus,
            consoleUri=self.consoleUri,
            subscriptionInfo=self.subscriptionInfo,
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPMachineInstanceList:
    items: list[CSPMachineInstance]
    count: int
    offset: int
    total: int

    def to_domain_model(self):
        return CSPMachineInstanceListModel(
            items=[item.to_domain_model() for item in self.items],
            count=self.count,
            offset=self.offset,
            total=self.total,
        )
