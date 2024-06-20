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
from common.enums.csp_type import CspType


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class NetworkInfo:
    privateIpAddress: str
    publicIpAddress: str
    publicIpAddressIsFloating: bool
    securityGroups: list[ObjectCspIdName]
    subnetInfo: ObjectNameResourceTypeId
    vpcInfo: ObjectNameResourceTypeId

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, NetworkInfo)
            and (self.privateIpAddress == other.privateIpAddress)
            and (self.publicIpAddress == other.publicIpAddress)
            and (self.publicIpAddressIsFloating == other.publicIpAddressIsFloating)
            and (len(self.securityGroups) == len(other.securityGroups))
            and {x.to_json() for x in self.securityGroups} == {x.to_json() for x in other.securityGroups}
            and (self.subnetInfo == other.subnetInfo)
            and (self.vpcInfo == other.vpcInfo)
        )


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

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, EC2CSPInfo)
            and (self.accessProfileId == other.accessProfileId)
            and (self.availabilityZone == other.availabilityZone)
            and (self.cpuCoreCount == other.cpuCoreCount)
            and (self.createdAt == other.createdAt)
            and (self.instanceType == other.instanceType)
            and (self.keyPairName == other.keyPairName)
            and (self.networkInfo == other.networkInfo)
            and (self.platform == other.platform)
            and (self.cspRegion == other.cspRegion)
            and (self.rootDevice == other.rootDevice)
            and (self.state == other.state)
            and (len(self.cspTags) == len(other.cspTags))
            and {x.to_json() for x in self.cspTags} == {x.to_json() for x in other.cspTags}
            and (self.virtualizationType == other.virtualizationType)
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class IpConfigurations:
    privateIpAddress: str
    publicIpAddress: str
    subnetInfo: ObjectNameResourceTypeId
    vpcInfo: ObjectNameResourceTypeId

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, IpConfigurations)
            and (self.publicIpAddress == other.publicIpAddress)
            and (self.privateIpAddress == other.privateIpAddress)
            and (self.subnetInfo.id == other.subnetInfo.id)
            and (self.vpcInfo.id == other.vpcInfo.id)
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AzureNetworkInfo:
    connections: list[IpConfigurations]
    securityGroups: list[ObjectCspIdName]

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, AzureNetworkInfo)
            and (len(self.connections) == len(other.connections))
            and {x.to_json() for x in self.connections} == {x.to_json() for x in other.connections}
            and (len(self.securityGroups) == len(other.securityGroups))
            and {x.to_json() for x in self.securityGroups} == {x.to_json() for x in other.securityGroups}
        )


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

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, AzureCSPInfo)
            and (self.availabilityZones == other.availabilityZones)
            and (self.cpuCoreCount == other.cpuCoreCount)
            and (self.createdAt == other.createdAt)
            and (self.instanceType == other.instanceType)
            and (self.keyPairName == other.keyPairName)
            and (self.networkInfo == other.networkInfo)
            and (self.platform == other.platform)
            and (self.cspRegion == other.cspRegion)
            and (self.rootDevice == other.rootDevice)
            and (self.state == other.state)
            and (len(self.cspTags) == len(other.cspTags))
            and {x.to_json() for x in self.cspTags} == {x.to_json() for x in other.cspTags}
        )


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

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, CSPMachineInstance)
            and (self.customerId == other.customerId)
            and (self.generation == other.generation)
            and (self.id == other.id)
            and (self.name == other.name)
            and (self.resourceUri == other.resourceUri)
            and (self.type == other.type)
            and (self.accountInfo == other.accountInfo)
            and (len(self.backupInfo) == len(other.backupInfo))
            and {x.to_json() for x in self.backupInfo} == {x.to_json() for x in other.backupInfo}
            and (self.cspId == other.cspId)
            and (self.cspName == other.cspName)
            and (self.cspType == other.cspType)
            and (self.cspInfo == other.cspInfo)
            and (len(self.protectionGroupInfo) == len(other.protectionGroupInfo))
            and {x.to_json() for x in self.protectionGroupInfo} == {x.to_json() for x in other.protectionGroupInfo}
            and (self.state == other.state)
            and (len(self.volumeAttachmentInfo) == len(other.volumeAttachmentInfo))
            and {x.to_json() for x in self.volumeAttachmentInfo} == {x.to_json() for x in other.volumeAttachmentInfo}
            and (len(self.protectionJobInfo) == len(other.protectionJobInfo))
            and {x.to_json() for x in self.protectionJobInfo} == {x.to_json() for x in other.protectionJobInfo}
            and (self.protectionStatus == other.protectionStatus)
            and (self.consoleUri == other.consoleUri)
        )


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPMachineInstanceList:
    items: list[CSPMachineInstance]
    count: int
    offset: int
    total: int
