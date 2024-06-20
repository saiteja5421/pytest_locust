from enum import Enum


class InventoryType(Enum):
    EC2_AND_EBS = "MACHINE_INSTANCES_AND_VOLUMES"
    RDS = "RDS"
    KUBERNETES = "KUBERNETES"
