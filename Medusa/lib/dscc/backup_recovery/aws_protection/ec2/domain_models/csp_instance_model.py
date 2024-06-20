import datetime

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


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class NetworkInfoModel:
    privateIpAddress: str
    publicIpAddress: str
    publicIpAddressIsFloating: bool
    securityGroups: list[ObjectCspIdName]
    subnetInfo: ObjectNameResourceTypeId
    vpcInfo: ObjectNameResourceTypeId


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class EC2CSPInfoModel:
    accessProfileId: str
    availabilityZone: str
    cpuCoreCount: int
    createdAt: datetime
    instanceType: str
    keyPairName: str
    networkInfo: NetworkInfoModel
    platform: str
    cspRegion: str
    rootDevice: str
    state: str
    cspTags: list[CSPTag]
    virtualizationType: str


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class IpConfigurationsModel:
    privateIpAddress: str
    publicIpAddress: str
    subnetInfo: ObjectNameResourceTypeId
    vpcInfo: ObjectNameResourceTypeId


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AzureNetworkInfoModel:
    connections: list[IpConfigurationsModel]
    securityGroups: list[ObjectCspIdName]


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class AzureCSPInfoModel:
    availabilityZones: list[str]
    cpuCoreCount: int
    createdAt: datetime
    instanceType: str
    keyPairName: str
    networkInfo: AzureNetworkInfoModel
    platform: str
    cspRegion: str
    rootDevice: str
    state: str
    cspTags: list[CSPTag]


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPMachineInstanceModel:
    customerId: str
    generation: int
    id: str
    name: str
    resourceUri: str
    type: str
    accountInfo: ObjectReferenceWithId
    backupInfo: list[ObjectCountType]
    cspId: str
    cspInfo: Union[EC2CSPInfoModel, AzureCSPInfoModel]
    cspName: str
    cspType: str
    protectionGroupInfo: list[ObjectNameResourceTypeId]
    state: str
    volumeAttachmentInfo: list[AttachmentInfo]
    protectionJobInfo: list[CspProtectionJobInfo]
    protectionStatus: str
    consoleUri: str = None
    subscriptionInfo: ObjectReferenceWithId = None


@dataclass_json(letter_case=LetterCase.CAMEL)
@dataclass
class CSPMachineInstanceListModel:
    items: list[CSPMachineInstanceModel]
    count: int
    offset: int
    total: int
