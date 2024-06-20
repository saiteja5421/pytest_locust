from abc import ABC, abstractmethod
from typing import List

from lib.common.enums.cvsa import CloudProvider, CloudRegions
from lib.platform.aws_boto3.models.instance import Tag
from lib.platform.cloud.cloud_dataclasses import CloudInstance, CloudInstanceState, CloudImage, CloudDisk


class CloudVmManager(ABC):
    @abstractmethod
    def name(self) -> CloudProvider:
        pass

    @abstractmethod
    def get_instance(self, instance_id: str) -> CloudInstance:
        pass

    @abstractmethod
    def list_instances(
        self, states: List[CloudInstanceState] = None, tags: List[Tag] | None = None, location: str = None
    ) -> List[CloudInstance]:
        pass

    @abstractmethod
    def list_images(self) -> List[CloudImage]:
        pass

    @abstractmethod
    def get_disk(self, disk_id: str) -> CloudDisk | None:
        pass

    @abstractmethod
    def start_instance(self, instance_id: str):
        pass

    @abstractmethod
    def stop_instance(self, instance_id: str):
        pass

    @abstractmethod
    def terminate_instance(self, instance_id: str):
        pass

    @abstractmethod
    def create_instance(
        self,
        image_id: str,
        tags: list[Tag],
        subnet_tag: Tag,
        instance_type: str = "",
        location: CloudRegions = None,
    ) -> CloudInstance:
        pass

    @abstractmethod
    def wait_cloud_instance_status_ok(self, instance_id: str):
        pass

    @abstractmethod
    def get_ntp_server_address(self) -> str:
        pass

    @abstractmethod
    def set_instance_tag(self, instance_id: str, key: str, value: str):
        pass


def cloud_vm_managers_names() -> List[str]:
    # # Azure tests temporary disabled
    # return ["azure", "aws"]
    return ["aws"]
