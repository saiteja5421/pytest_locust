from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

from lib.common.enums.cvsa import CloudProvider
from lib.platform.aws_boto3.models.instance import Tag


class CloudInstanceState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SHUTTINGDOWN = "shuttingDown"
    SHUTTING_DOWN = "shutting-down"
    STOPPED = "stopped"
    STOPPING = "stopping"
    TERMINATED = "terminated"
    STARTING = "starting"
    UNKNOWN = "unknown"
    DEALLOCATED = "deallocated"
    DEALLOCATING = "deallocating"

    @classmethod
    def list(cls) -> List[CloudInstanceState]:
        statuses = [cls(state.value) for state in cls]
        statuses.remove(CloudInstanceState.UNKNOWN)
        return statuses

    @classmethod
    def list_not_terminated(cls) -> List[CloudInstanceState]:
        statuses = [cls(state.value) for state in cls]
        statuses.remove(CloudInstanceState.UNKNOWN)
        statuses.remove(CloudInstanceState.TERMINATED)
        statuses.remove(CloudInstanceState.SHUTTINGDOWN)
        statuses.remove(CloudInstanceState.SHUTTING_DOWN)
        statuses.remove(CloudInstanceState.DEALLOCATED)
        statuses.remove(CloudInstanceState.DEALLOCATING)
        return statuses


@dataclass
class CloudImage:
    id: str
    name: str
    tags: Optional[List[Tag]] = None
    version: Optional[str] = None


@dataclass
class CloudDisk:
    disk_size_bytes: int
    name: str
    tags: List[Tag]
    instance_id: Optional[str] = None
    device: Optional[str] = None
    state: Optional[str] = None


@dataclass
class CloudSubnet:
    id: str
    tags: List[Tag]


@dataclass
class CloudInstance:
    id: str
    instance_type: str
    location: str
    public_ip: str
    private_ip: str
    launch_time: datetime
    tags: List[Tag]
    # cloud objects
    image: CloudImage
    cloud_provider: CloudProvider
    state: CloudInstanceState
    subnets: List[CloudSubnet]
    data_disks: List[CloudDisk]
    os_disk: Optional[CloudDisk] = None
