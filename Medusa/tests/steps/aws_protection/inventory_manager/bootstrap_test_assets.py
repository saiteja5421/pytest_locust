import logging
import uuid
from lib.common.enums.ebs_volume_type import EBSVolumeType
from lib.common.enums.kafka_inventory_asset_type import KafkaInventoryAssetType
from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.aws_boto3.models.instance import Tag
from lib.common.enums.ami_image_ids import AMIImageIDs
import tests.steps.aws_protection.assets.ec2_ebs_steps as EC2EBSSteps

logger = logging.getLogger()

ASSET_INDEX = "index"


def bootstrap_test_ec2_assets(
    aws: AWS, ec2_asset_catalogue: list, ec2_key_name: str, ec2_image_id: str, tags: list[Tag] = None
) -> tuple[dict, dict]:
    """Creates EC2 instances and EBS volumes attached to the instances

    Args:
        aws (AWS): AWS account
        ec2_asset_catalogue (list): EC2 assets
        ec2_key_name (str): EC2 key name
        ec2_image_id (str): EC2 image id
        tags (list[Tag], optional): EC2 tags. Defaults to None.

    Returns:
        tuple[dict, dict]: EC2 instances that are created and EBS volumes that are created
    """
    ec2_assets = {}
    volume_assets = {}
    asset_tags = tags
    if tags is None:
        asset_tags = [Tag(Key="Automation-" + ec2_key_name, Value="Python-Automation")]
        aws.ec2.create_ec2_key_pair(key_name=ec2_key_name)

    for requested_asset in ec2_asset_catalogue:
        ec2_index = requested_asset[ASSET_INDEX]
        requested_volumes = requested_asset[KafkaInventoryAssetType.ASSET_TYPE_VOLUME]
        ec2_instances = aws.ec2.create_ec2_instance(
            key_name=ec2_key_name,
            image_id=ec2_image_id,
            tags=asset_tags,
        )
        ec2_assets[ec2_index] = {}

        volumes = {}
        for volume in requested_volumes:
            # Creating EBS Volume
            volume_index = volume[ASSET_INDEX]
            ebs_volume = aws.ebs.create_ebs_volume(
                size=1,
                volume_type=EBSVolumeType.GP2.value,
                tags=tags,
            )
            # Attaching EBS volume to the EC2 instance
            aws.ebs.attach_volume_to_ec2_instance(
                volume_id=ebs_volume.id, device="/dev/sdh{}".format(volume_index), instance_id=ec2_instances[0].id
            )
            volumes[volume_index] = ebs_volume
            volume_assets[volume_index] = ebs_volume
        ec2_assets[ec2_index][KafkaInventoryAssetType.ASSET_TYPE_MACHINE_INSTANCE] = ec2_instances[0]
        ec2_assets[ec2_index][KafkaInventoryAssetType.ASSET_TYPE_VOLUME] = volumes

    return ec2_assets, volume_assets


def _bootstrap_standard_test_ec2_assets(
    aws: AWS,
    ec2_count: int,
    attached_volume_count: int = 0,
    tags: list[Tag] = None,
    ec2_key_pattern: str = None,
    ebs_key_pattern: str = None,
) -> tuple[str, dict, dict, dict]:
    """Creates standard EC2 assets with EBS volumes

    Args:
        aws (AWS): AWS account
        ec2_count (int): Number of EC2 instances to create
        attached_volume_count (int, optional): Number of volumes attached to the instance. Defaults to 0.
        tags (list[Tag], optional): EC2 tags. Defaults to None.
        ec2_key_pattern (str, optional): EC2 key pattern. Defaults to None.
        ebs_key_pattern (str, optional): EBS key pattern. Defaults to None.

    Returns:
        tuple[str, dict, dict, dict]:
            EC2 key name, master assets, ec2 instances, ebs volumes
    """
    ec2_key_name = "ec2-key-" + str(uuid.uuid4())
    master_assets = {}
    ec2_assets = {}
    volume_assets = {}
    asset_tags = tags
    volume_count = 0
    if tags is None:
        asset_tags = [Tag(Key="Automation-" + ec2_key_name, Value="Python-Automation")]
        aws.ec2.create_ec2_key_pair(key_name=ec2_key_name)

    for ec2_index in range(ec2_count):
        ec2_instances = aws.ec2.create_ec2_instance(
            key_name=ec2_key_name,
            image_id=AMIImageIDs.AMAZON_LINUX_US_WEST_1.value,
            tags=asset_tags,
        )
        ec2_dict_index = ec2_index
        if ec2_key_pattern is not None:
            ec2_dict_index = ec2_key_pattern.format(counter=ec2_index + 1)

        master_assets[ec2_dict_index] = {}

        volumes = {}
        for vol_index in range(attached_volume_count):
            # Creating EBS Volume
            ebs_volume = aws.ebs.create_ebs_volume(
                size=1,
                volume_type=EBSVolumeType.GP2.value,
                tags=tags,
            )
            vol_dict_index = volume_count
            if ebs_key_pattern is not None:
                vol_dict_index = ebs_key_pattern.format(counter=vol_index + 1)
                vol_dict_index = "{}-{}".format(ec2_dict_index, vol_dict_index)
            # Attaching EBS volume to the EC2 instance
            aws.ebs.attach_volume_to_ec2_instance(
                volume_id=ebs_volume.id, device="/dev/sdh{}".format(vol_dict_index), instance_id=ec2_instances[0].id
            )
            volumes[vol_dict_index] = ebs_volume
            volume_assets[vol_dict_index] = ebs_volume
            volume_count = volume_count + 1

        ec2_assets[ec2_dict_index] = ec2_instances[0]
        master_assets[ec2_dict_index][KafkaInventoryAssetType.ASSET_TYPE_MACHINE_INSTANCE] = ec2_instances[0]
        master_assets[ec2_dict_index][KafkaInventoryAssetType.ASSET_TYPE_VOLUME] = volumes

    return ec2_key_name, master_assets, ec2_assets, volume_assets


def _bootstrap_standard_test_ebs_assets(
    aws: AWS,
    volume_count: int,
    tags: list[Tag] = None,
    ebs_key_pattern: str = None,
) -> dict:
    """Creates standard EBS assets

    Args:
        aws (AWS): AWS account
        volume_count (int): Number of volumes to create
        tags (list[Tag], optional): EBS tags. Defaults to None.
        ebs_key_pattern (str, optional): EBS key pattern. Defaults to None.

    Returns:
        dict: EBS volumes
    """
    volume_assets = {}
    for vol_index in range(volume_count):
        # Creating EBS Volume
        ebs_volume = aws.ebs.create_ebs_volume(
            size=1,
            volume_type=EBSVolumeType.GP2.value,
            tags=tags,
        )
        vol_dict_index = vol_index
        if ebs_key_pattern is not None:
            vol_dict_index = ebs_key_pattern.format(counter=vol_index + 1)
        volume_assets[vol_dict_index] = ebs_volume
    return volume_assets


def destroy_test_ebs_assets(aws: AWS, volume_assets: dict, deleted_ebs_instances: dict):
    """Delete EBS volumes

    Args:
        aws (AWS): AWS account
        volume_assets (dict): EBS volumes
        deleted_ebs_instances (dict): deleted volumes
    """
    for _, vol_val in volume_assets.items():
        if deleted_ebs_instances is None or vol_val.id not in deleted_ebs_instances:
            aws.ebs.delete_volume(volume_id=vol_val.id)


def destroy_test_ec2_assets(
    aws: AWS,
    ec2_assets: dict,
    ec2_key_name: str = None,
    deleted_ec2_instances: dict = None,
    deleted_ebs_instances: dict = None,
):
    """Delete EC2 instances

    Args:
        aws (AWS): AWS account
        ec2_assets (dict): EC2 instances
        ec2_key_name (str, optional): EC2 key name. Defaults to None.
        deleted_ec2_instances (dict, optional): Deleted instances. Defaults to None.
        deleted_ebs_instances (dict, optional): Deleted volumes. Defaults to None.
    """
    for _, ec2_val in ec2_assets.items():
        ec2 = ec2_val[KafkaInventoryAssetType.ASSET_TYPE_MACHINE_INSTANCE]
        vols = ec2_val[KafkaInventoryAssetType.ASSET_TYPE_VOLUME]
        for vol_key, vol_val in vols.items():
            if deleted_ebs_instances is None or vol_val.id not in deleted_ebs_instances:
                EC2EBSSteps.detach_and_delete_volume(
                    aws=aws, volume_id=vol_val.id, device="/dev/sdh{}".format(vol_key), instance_id=ec2.id
                )
        if deleted_ec2_instances is None or ec2.id not in deleted_ec2_instances:
            aws.ec2.stop_and_terminate_ec2_instance(ec2_instance_id=ec2.id)
    if ec2_key_name is not None:
        aws.ec2.delete_key_pair(key_name=ec2_key_name)


def _detach_and_delete_ebs_volume(
    aws: AWS,
    ec2_assets: dict,
    volume_id: str,
) -> bool:
    """Detaches volume from instance and deletes it

    Args:
        aws (AWS): AWS account
        ec2_assets (dict): EC2 assets
        volume_id (str): Volume id

    Returns:
        bool: If True, volume is found and deleted
    """
    for _, ec2_val in ec2_assets.items():
        ec2 = ec2_val[KafkaInventoryAssetType.ASSET_TYPE_MACHINE_INSTANCE]
        vols = ec2_val[KafkaInventoryAssetType.ASSET_TYPE_VOLUME]
        for vol_key, vol_val in vols.items():
            if vol_val.id is volume_id:
                EC2EBSSteps.detach_and_delete_volume(
                    aws=aws, volume_id=vol_val.id, device="/dev/sdh{}".format(vol_key), instance_id=ec2.id
                )
                return True
    return False


class BootstrapTestbed:
    """This class is to track testbed assets and exposes functionalities for asset life cycle management."""

    def __init__(
        self,
        aws: AWS,
    ):
        self._aws = aws
        self._master_asset_tracker = []
        self._master_ebs_tracker = []
        self._ec2_key_name = []
        self._deleted_ebs_instances = {}
        self._deleted_ec2_instances = {}

    def create_ec2_instances(
        self,
        ec2_count: int,
        attached_volume_count: int,
        tags: list[Tag] = None,
        ec2_key_pattern: str = None,
        ebs_key_pattern: str = None,
    ) -> tuple[dict, dict, dict]:
        """create bulk ec2 instance

        Args:
            ec2_count (int): Number of ec2 instance
            attached_volume_count (int): Number of volumes attached to each ec2 instances
            tags (list[Tag], optional): AWS Tag for the asset
            ec2_key_pattern (str, optional): Asset key pattern for the ec2 asset returned as part of the dictionary.
            ebs_key_pattern (str, optional): Asset key pattern for the ebs asset returned as part of the dictionary.

        Returns:
            tuple[dict, dict, dict]
        """
        ec2_key_name, master_assets, ec2_assets, volume_assets = _bootstrap_standard_test_ec2_assets(
            aws=self._aws,
            ec2_count=ec2_count,
            attached_volume_count=attached_volume_count,
            tags=tags,
            ec2_key_pattern=ec2_key_pattern,
            ebs_key_pattern=ebs_key_pattern,
        )
        self._master_asset_tracker.append(master_assets)
        self._ec2_key_name.append(ec2_key_name)
        return master_assets, ec2_assets, volume_assets

    def create_ebs_instances(
        self,
        volume_count: int,
        tags: list[Tag] = None,
        ebs_key_pattern: str = None,
    ) -> dict:
        """Create bulk ebs volumes

        Args:
            volume_count (int): Number of ebs volumes
            tags (list[Tag], optional): AWS Tag for the asset. Defaults to None.
            ebs_key_pattern (str, optional): _description_. Defaults to None.

        Returns:
            dict: volume assets
        """
        volume_assets = _bootstrap_standard_test_ebs_assets(
            aws=self._aws,
            volume_count=volume_count,
            tags=tags,
            ebs_key_pattern=ebs_key_pattern,
        )
        self._master_ebs_tracker.append(volume_assets)
        return volume_assets

    def delete_ebs_instance(self, volume_id: str):
        """Deletes EBS asset

        Args:
            volume_id (str): EBS id
        """
        vol_deleted = False
        for asset in self._master_asset_tracker:
            vol_deleted = _detach_and_delete_ebs_volume(aws=self._aws, ec2_assets=asset, volume_id=volume_id)
        if not vol_deleted:
            self._aws.ebs.delete_volume(volume_id)
        self._deleted_ebs_instances[volume_id] = volume_id

    def terminate_ec2_instance(self, ec2_instance_id: str, wait: bool = True):
        """Deletes EC2 instance

        Args:
            ec2_instance_id (str): EC2 instance id
            wait (bool, optional): Wait for asset to be terminated. Defaults to True.
        """
        self._aws.ec2.stop_and_terminate_ec2_instance(ec2_instance_id=ec2_instance_id, wait=wait)
        self._deleted_ec2_instances[ec2_instance_id] = ec2_instance_id

    def destroy(
        self,
    ):
        """Destroys all the assets maintained in testbed instance"""
        for asset in self._master_asset_tracker:
            destroy_test_ec2_assets(
                aws=self._aws,
                ec2_assets=asset,
                deleted_ec2_instances=self._deleted_ec2_instances,
                deleted_ebs_instances=self._deleted_ebs_instances,
            )
        for asset in self._master_ebs_tracker:
            destroy_test_ebs_assets(
                aws=self._aws,
                volume_assets=asset,
                deleted_ebs_instances=self._deleted_ebs_instances,
            )
        for key in self._ec2_key_name:
            self._aws.ec2.delete_key_pair(key_name=key)
