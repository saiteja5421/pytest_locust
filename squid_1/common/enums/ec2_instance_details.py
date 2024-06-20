from dataclasses import dataclass
from enum import Enum


@dataclass
class Ec2InstanceDetails:
    instance_type: str
    cpu: int
    ram: int


class InstanceDetails(Enum):
    C6I_LARGE = Ec2InstanceDetails("c6i.large", 2, 4)
    R6I_LARGE = Ec2InstanceDetails("r6i.large", 2, 16)
    C6I_XLARGE = Ec2InstanceDetails("c6i.xlarge", 2, 8)
    M6I_XLARGE = Ec2InstanceDetails("m6i.xlarge", 4, 16)
    R6I_XLARGE = Ec2InstanceDetails("r6i.xlarge", 4, 32)
    C6I_2XLARGE = Ec2InstanceDetails("c6i.2xlarge", 8, 16)
    M6I_2XLARGE = Ec2InstanceDetails("m6i.2xlarge", 8, 32)
    R6I_2XLARGE = Ec2InstanceDetails("r6i.2xlarge", 8, 64)
    C6I_4XLARGE = Ec2InstanceDetails("c6i.4xlarge", 16, 32)
    M6I_4XLARGE = Ec2InstanceDetails("m6i.4xlarge", 16, 64)
    R6I_4XLARGE = Ec2InstanceDetails("r6i.4xlarge", 16, 128)
    C6I_8XLARGE = Ec2InstanceDetails("c6i.8xlarge", 32, 64)
    M6I_8XLARGE = Ec2InstanceDetails("m6i.8xlarge", 32, 128)
    R6I_8XLARGE = Ec2InstanceDetails("r6i.8xlarge", 32, 256)
    C6I_12XLARGE = Ec2InstanceDetails("c6i.12xlarge", 48, 96)
    M6I_12XLARGE = Ec2InstanceDetails("m6i.12xlarge", 48, 192)
    R6I_12XLARGE = Ec2InstanceDetails("r6i.12xlarge", 48, 384)
    C6I_16XLARGE = Ec2InstanceDetails("c6i.16xlarge", 64, 128)
    M6I_16XLARGE = Ec2InstanceDetails("m6i.16xlarge", 64, 256)
    R6I_16XLARGE = Ec2InstanceDetails("r6i.16xlarge", 64, 512)
    C6I_24XLARGE = Ec2InstanceDetails("c6i.24xlarge", 96, 192)
    M6I_24XLARGE = Ec2InstanceDetails("m6i.24xlarge", 96, 384)
    R6I_24XLARGE = Ec2InstanceDetails("r6i.24xlarge", 96, 768)
    C6I_32XLARGE = Ec2InstanceDetails("c6i.32xlarge", 128, 256)
    M6I_32XLARGE = Ec2InstanceDetails("m6i.32xlarge", 128, 512)
    R6I_32XLARGE = Ec2InstanceDetails("r6i.32xlarge", 128, 1024)
