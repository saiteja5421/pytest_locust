from datetime import datetime
from typing import Optional

from lib.platform.aws_boto3.models.base.pydantic_model import Base


class Tag(Base):
    Key: str
    Value: str


class Monitoring(Base):
    State: str


class Placement(Base):
    AvailabilityZone: str
    GroupName: str
    Tenancy: str


class State(Base):
    Code: int
    Name: str


class EBS(Base):
    AttachTime: datetime
    DeleteOnTermination: bool
    Status: str
    VolumeId: str


class BlockDeviceMapping(Base):
    DeviceName: str
    Ebs: EBS


class Attachment(Base):
    AttachTime: datetime
    AttachmentId: str
    DeleteOnTermination: bool
    DeviceIndex: int
    Status: str


class Group(Base):
    GroupName: str
    GroupId: str


class IpAddress(Base):
    Primary: bool
    PrivateIpAddress: str


class NetworkInterface(Base):
    Attachment: Attachment
    Description: str
    Groups: list[Group]
    Ipv6Addresses: list
    MacAddress: str
    NetworkInterfaceId: str
    OwnerId: str
    PrivateIpAddress: str
    PrivateIpAddresses: list[IpAddress]
    SourceDestCheck: bool
    Status: str
    SubnetId: str
    VpcId: str
    InterfaceType: str


class StateReason(Base):
    Code: str
    Message: str


class CpuOptions(Base):
    CoreCount: int
    ThreadsPerCore: int


class CapacityReservationSpecification(Base):
    CapacityReservationPreference: str


class MetadataOptions(Base):
    State: str
    HttpTokens: str
    HttpPutResponseHopLimit: int
    HttpEndpoint: str


class HibernationOption(Base):
    Configured: bool


class PrivateDnsNameOptions(Base):
    HostnameType: str
    EnableResourceNameDnsARecord: bool
    EnableResourceNameDnsAAAARecord: bool


class EnclaveOptions(Base):
    Enabled: bool


class Instance(Base):
    AmiLaunchIndex: Optional[int]
    ImageId: Optional[str]
    InstanceId: Optional[str]
    InstanceType: Optional[str]
    KeyName: Optional[str]
    LaunchTime: Optional[datetime]
    Monitoring: Optional[Monitoring]
    Placement: Optional[Placement]
    PrivateDnsName: Optional[str]
    PrivateIpAddress: Optional[str]
    ProductCodes: Optional[list]
    PublicDnsName: Optional[str]
    PublicIpAddress: Optional[str]
    State: Optional[State]
    StateTransitionReason: Optional[str]
    SubnetId: Optional[str]
    VpcId: Optional[str]
    Architecture: Optional[str]
    BlockDeviceMappings: Optional[list[BlockDeviceMapping]]
    ClientToken: Optional[str]
    EbsOptimized: Optional[bool]
    EnaSupport: Optional[bool]
    Hypervisor: Optional[str]
    NetworkInterfaces: Optional[list[NetworkInterface]]
    RootDeviceName: Optional[str]
    RootDeviceType: Optional[str]
    SecurityGroups: Optional[list[Group]]
    SourceDestCheck: Optional[bool]
    StateReason: Optional[StateReason]
    Tags: Optional[list[Tag]]
    VirtualizationType: Optional[str]
    CpuOptions: Optional[CpuOptions]
    CapacityReservationSpecification: Optional[CapacityReservationSpecification]
    HibernationOptions: Optional[HibernationOption]
    MetadataOptions: Optional[MetadataOptions]
    EnclaveOptions: Optional[EnclaveOptions]
    PlatformDetails: Optional[str]
    UsageOperation: Optional[str]
    UsageOperationUpdateTime: Optional[datetime]
    PrivateDnsNameOptions: Optional[PrivateDnsNameOptions]
