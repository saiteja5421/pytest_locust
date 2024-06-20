from lib.platform.aws.models.base.pydantic_model import Base

"""
Class for Elastic IP
"""


class Address(Base):
    InstanceId: str = None
    PublicIp: str = None
    AllocationId: str = None
    AssociationId: str = None
    Domain: str = None
    NetworkInterfaceOwnerId: str = None
    PrivateIpAddress: str = None
    PublicIpv4Pool: str = None
    NetworkBorderGroup: str = None
