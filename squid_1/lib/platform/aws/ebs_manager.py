import logging
from typing import Callable

import boto3
from waiting import wait, TimeoutExpired

from common.enums.ebs_volume_type import EBSVolumeType
from lib.platform.aws.models.instance import Tag
from lib.platform.aws.client_config import ClientConfig

logger = logging.getLogger()


class EBSManager:
    def __init__(
        self, aws_session: Callable[[], boto3.Session], endpoint_url: str = None, client_config: ClientConfig = None
    ):
        self.get_session = aws_session
        self.endpoint_url = endpoint_url
        self.client_config = client_config

    @property
    def ec2_resource(self):
        return self.get_session().resource("ec2", endpoint_url=self.endpoint_url, config=self.client_config)

    @property
    def ec2_client(self):
        return self.get_session().client("ec2", endpoint_url=self.endpoint_url, config=self.client_config)

    @property
    def ebs_client(self):
        return self.get_session().client("ebs", endpoint_url=self.endpoint_url, config=self.client_config)

    """
    volume_type = gp2 | gp3 | io1 | io2 | st1 | sci | standard
    AvailabilityZone = "us-east-1d"
    """

    def create_ebs_volume(
        self,
        size: int,
        volume_type: str,
        tags: list[Tag] = [],
        resource_type: str = "volume",
        encrypted=False,
        availability_zone: str = "",
    ):
        new_volume = None

        logger.info(f"Creating EBS Volumes in AZ={availability_zone}, Volume Type={volume_type}")

        if not tags:
            new_volume = self.ec2_resource.create_volume(
                AvailabilityZone=availability_zone,
                Size=size,
                VolumeType=volume_type,
                Encrypted=encrypted,
            )
        else:
            # converting list[Tag] to list[{Tag}]
            tags_list = [dict(tag) for tag in tags]
            new_volume = self.ec2_resource.create_volume(
                AvailabilityZone=availability_zone,
                Size=size,
                VolumeType=volume_type,
                Encrypted=encrypted,
                TagSpecifications=[{"ResourceType": resource_type, "Tags": tags_list}],
            )

        logger.info(f"New Volume = {new_volume}")

        logger.info(f"Waiting for volume {new_volume.id} to become 'Available'")
        waiter = self.ec2_client.get_waiter("volume_available")
        waiter.wait(VolumeIds=[new_volume.id])

        return new_volume

    """
    volume_type = gp3 | io1 | io2 (only io1 and io2 are multi-attach volumes but Iops is needed for gp3)
    AvailabilityZone = "us-east-1d"
    Iops valid values:
    gp3 : 3,000-16,000 IOPS
    io1 : 100-64,000 IOPS
    io2 : 100-64,000 IOPS
    """

    def create_multi_attach_ebs_volume(
        self,
        availability_zone: str,
        size: int,
        volume_type: str,
        tags: list[Tag] = [],
        resource_type: str = "volume",
        multi_attach_enabled: bool = True,
        iops: int = 100,
        encrypted=False,
    ):
        new_volume = None

        logger.info(f"Creating EBS Volumes in AZ={availability_zone}, Volume Type={volume_type}")

        if not tags:
            new_volume = self.ec2_resource.create_volume(
                AvailabilityZone=availability_zone,
                Size=size,
                VolumeType=volume_type,
                Iops=iops,
                MultiAttachEnabled=multi_attach_enabled,
                Encrypted=encrypted,
            )
        else:
            # converting list[Tag] to list[{Tag}]
            tags_list = [dict(tag) for tag in tags]
            new_volume = self.ec2_resource.create_volume(
                AvailabilityZone=availability_zone,
                Size=size,
                Iops=iops,
                MultiAttachEnabled=multi_attach_enabled,
                VolumeType=volume_type,
                Encrypted=encrypted,
                TagSpecifications=[{"ResourceType": resource_type, "Tags": tags_list}],
            )

        logger.info(f"New Volume = {new_volume}")
        return new_volume

    def get_all_volumes(self):
        volumes = self.ec2_resource.volumes.all()
        return [volume for volume in volumes]

    def get_volumes_id_by_tag(self, tag: Tag) -> list:
        volumes = self.ec2_resource.volumes.all()
        return [volume.id for volume in volumes if volume.tags and dict(tag) in volume.tags]

    """
    tag_values = list of [tag_values]
    """

    def filter_ebs_volumes_by_tag(self, tag_name: str, tag_values: list[str]):
        volumes = self.ec2_resource.volumes.filter(Filters=[{"Name": f"tag:{tag_name}", "Values": tag_values}])
        for volume in volumes:
            logger.info(f" ----- Volume ID: {volume.id} ----- ")

        return volumes

    def create_and_attach_volumes_to_ec2_instance(
        self,
        ec2_id,
        volumes_count,
        encrypted=False,
        availability_zone: str = None,
    ):
        ebs_volume_id_list = []
        ebs_device_name_list = []
        for vol in range(volumes_count):
            ebs_volume = self.create_ebs_volume(
                availability_zone=availability_zone,
                size=100,
                volume_type=EBSVolumeType.GP2.value,
                encrypted=encrypted,
            )
            assert ebs_volume is not None, "Failed to create AWS EBS Volume"
            device_name = f"/dev/sda{vol}"
            self.attach_volume_to_ec2_instance(
                volume_id=ebs_volume.id,
                device=device_name,
                instance_id=ec2_id,
            )
            ebs_volume_id_list.append(ebs_volume.id)
            ebs_device_name_list.append(device_name)
        return ebs_volume_id_list, ebs_device_name_list

    def attach_volume_to_ec2_instance(self, volume_id: str, device: str, instance_id: str):
        """
        Refer the following link for 'Device' parameter applicable values
        https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/device_naming.html
        example value for device = /dev/sdh
        """
        volume = self.ec2_resource.Volume(volume_id)

        logger.info("Waiting for volume to be Available...")
        waiter = self.ec2_client.get_waiter("volume_available")
        waiter.wait(VolumeIds=[volume.id])
        volume.load()

        volume.attach_to_instance(Device=device, InstanceId=instance_id)

        logger.info(f"Waiting for {volume.id} to be attached to Instance {instance_id}")
        waiter = self.ec2_client.get_waiter("volume_in_use")
        waiter.wait(VolumeIds=[volume.id])
        logger.info(f"Volume {volume.id} is now attached to Instance {instance_id}. Its state is {volume.state}")

    def detach_volume_from_instance(self, volume_id: str, device: str, instance_id: str, force: bool = False):
        volume = self.ec2_resource.Volume(volume_id)

        if volume.state == "in-use":
            volume.detach_from_instance(Device=device, InstanceId=instance_id, Force=force)

        # Wait for volume to become available
        waiter = self.ec2_client.get_waiter("volume_available")
        waiter.wait(VolumeIds=[volume.id])

        logger.info(f"Volume {volume.id} detached from Instance {instance_id}.Volume State is {volume.state}")

    def delete_volume(self, volume_id: str):
        volume = self.ec2_resource.Volume(volume_id)
        volume.delete()

    def delete_volumes(self, volumes):
        for volume in volumes:
            volume = self.ec2_resource.Volume(volume)
            volume.delete()

    def get_volumes_attached_to_instances(self, instance_ids: list[str]):
        volumes = self.ec2_resource.volumes.filter(Filters=[{"Name": "attachment.instance-id", "Values": instance_ids}])
        return volumes

    def get_ebs_volume_by_id(self, volume_id: str):
        ebs_volume = self.ec2_resource.Volume(volume_id)
        return ebs_volume

    def get_ebs_volume_tags(self, volume_id: str) -> list[Tag]:
        ebs_volume = self.get_ebs_volume_by_id(volume_id)
        return [Tag(**tag) for tag in ebs_volume.tags]

    """
    Get the Device name of Attached EBS volume to the EC2 instance
    """

    def get_ec2_instance_attached_volume_device_name(self, volume_id: str, ec2_instance_id: str):
        ebs_volume = self.get_ebs_volume_by_id(volume_id)
        for attachment in ebs_volume.attachments:
            if attachment["InstanceId"] == ec2_instance_id:
                return attachment["Device"]

    def create_ebs_volume_tags(self, volume, tags_list: list[Tag]) -> None:
        tags_dict = [dict(tag) for tag in tags_list]
        tags = volume.create_tags(Tags=tags_dict)
        logger.info(f" ------ {tags} ----- ")

    """
    Delete / Remove EBS Volume Tags:

    Refer to -> aws.ec2.remove_tags_from_different_aws_resources_by_id()

    remove_ebs_volume_tags() & remove_tags_from_volumes() were removed
    """

    # NOTE: downloaded "ec2-api.pdf" from AWS. "CreateSnapshot" section: Page 290
    def create_ebs_volume_snapshot(self, volume_id: str, description: str = ""):
        """Create an AWS Snapshot for the given EBS Volume

        Args:
            volume_id (str): The Volume ID for which to take a snapshot
            description (str, optional): A description for the new snapshot. Defaults to ""
        Returns:
            new_snapshot: The new snapshot data: CreateSnapshotResponse
        """
        logger.info(f"Taking snapshot of volume_id: {volume_id}")
        new_snapshot = self.ec2_resource.create_snapshot(VolumeId=volume_id, Description=description)
        logger.info(f" ------ {new_snapshot} ----- ")

        # wait for snapshot completion
        waiter = self.ec2_client.get_waiter("snapshot_completed")
        waiter.wait(SnapshotIds=[new_snapshot.id])

        return new_snapshot

    def start_snapshot(self, volume_size_gb: int = 1, description: str = "start_snapshot"):
        """Start an AWS Snapshot, it will create snapshot in pending state that alow stream data and after that complete snapshot

        Args:
            volume_size_gb (int): size of data that will be streamed
            description (str, optional): A description for the new snapshot. Defaults to "start_snapshot"
        Returns:
            snapshotId - Id of started snapshot
        """
        logger.info("Starting snapshot")
        started_snapshot = self.ebs_client.start_snapshot(VolumeSize=volume_size_gb, Description=description)
        logger.info(f" ------ {started_snapshot} ----- ")

        return started_snapshot["SnapshotId"]

    def complete_snapshot(self, snapshot_id: int, changed_blocks_count: int):
        """Complete an AWS Snapshot

        Args:
            snapshot_id (int): snapshot id returned by start_snapshot method
            changed_blocks_count (str, optional): changed blocks can be returned from data extractor read data job or from snapshot API
        """
        logger.info("Complete snapshot in progress")

        def _wait_for_status_completed():
            complete_snapshot = self.ebs_client.complete_snapshot(
                SnapshotId=snapshot_id, ChangedBlocksCount=changed_blocks_count
            )
            if complete_snapshot["Status"] == "completed":
                return complete_snapshot

        try:
            snapshot_job = wait(_wait_for_status_completed, timeout_seconds=180, sleep_seconds=5)
        except TimeoutExpired as e:
            logger.error(f"Snapshot was not completed: {e}")
            raise e

        logger.info(f"Snapshot completed: {snapshot_job}")

    def create_volume_from_snapshot(self, availability_zone: str, snapshot_id: int, name: str):
        """Creating EBS volume from a Snapshot

        Args:
            availability_zone (str): availability zone for volume. If you want to attach it to ec2 az should be the same
            snapshot_id (int): snapshot id of source
            name (str): name tag value for volume
        Returns:
            snapshotId - Id of started snapshot
        """
        logger.info(f"Starting creating of ebs from snapshot {snapshot_id}")

        new_volume = self.ec2_resource.create_volume(
            AvailabilityZone=availability_zone,
            SnapshotId=snapshot_id,
            VolumeType="gp2",
            TagSpecifications=[
                {
                    "ResourceType": "volume",
                    "Tags": [
                        {
                            "Key": "Name",
                            "Value": name,
                        },
                        {
                            "Key": "Description",
                            "Value": "Restored by DE integration test",
                        },
                    ],
                }
            ],
        )
        logger.info(f" ------ Volume: {new_volume.id}, from {snapshot_id} ----- ")
        return new_volume

    """
    Modify EBS Volume
    volume_type = gp2 | gp3 | io1 | io2 | st1 | sci | standard
    """

    def modify_ebs_volume(
        self,
        volume_id: str,
        volume_type: str = "",
        volume_size: int = 0,
        volume_state: str = "volume_in_use",
        wait_filters: list = [],
    ):
        """Modifies the EBS Volume & wait for that task to complete

        Args:
            volume_id (str): target ebs_volume id
            volume_type (str): target ebs_volume type
            volume_size (int): target ebs_volume size to modify to
            volume_state (str): expected volume state after modifying volume -> 'volume_available', 'volume_in_use', 'volume_deleted'
            wait_filters (list): filter used for expected values of ebs_volume after modifying -> [{'Name': 'string','Values': ['string',]},]
                https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Waiter.VolumeInUse
        """

        if volume_type and volume_size:
            response = self.ec2_client.modify_volume(VolumeId=volume_id, Size=volume_size, VolumeType=volume_type)
        elif volume_size:
            response = self.ec2_client.modify_volume(VolumeId=volume_id, Size=volume_size)
        elif volume_type:
            response = self.ec2_client.modify_volume(VolumeId=volume_id, VolumeType=volume_type)

        # Waiter will poll ec2_client.describe_volumes() every 15 seconds until a successful state is reached
        # Error is returned after 40 failed checks
        waiter = self.ec2_client.get_waiter(volume_state)
        waiter.wait(Filters=wait_filters, VolumeIds=[volume_id])
        return response

    # From: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.delete_snapshot
    def delete_snapshot(self, snapshot_id: str, dry_run: bool = False):
        """Deletes the specified snapshot

        Args:
            snapshot_id (str): The ID of the EBS snapshot
            dry_run (bool, optional): Checks whether you have the required permissions for the action, without actually
            making the request, and provides an error response. If you have the required permissions, the error response
            is DryRunOperation. Otherwise, it is UnauthorizedOperation. Defaults to False.

        Returns:
            str: If the command succeeds, no output is returned
        """
        return_result: str = None
        response = self.ec2_client.delete_snapshot(SnapshotId=snapshot_id, DryRun=dry_run)
        # Error format from: https://docs.aws.amazon.com/AWSEC2/latest/APIReference/errors-overview.html#api-error-response
        if response:
            return_result = response["ResponseMetadata"]["HTTPStatusCode"]
        return return_result

    def get_all_snapshots(self):
        snapshots = self.ec2_client.describe_snapshots(OwnerIds=["self"])
        return snapshots

    def delete_all_snapshots(self):
        snapshots = self.get_all_snapshots()
        for snapshot in snapshots["Snapshots"]:
            self.delete_snapshot(snapshot["SnapshotId"])

    def get_snapshot_by_id(self, snapshot_id: str):
        snapshot = self.ec2_resource.Snapshot(snapshot_id)
        logger.info(f"Snapshot with ID {snapshot_id} is {snapshot}")
        return snapshot

    def get_snapshot_by_tag(self, tag: Tag):
        """Returns a EC2 snapshot 'resource' object if it contains the provided tag
        # NOTE:
        This method can be used to find the snapshots imported in DSCC if we provide a unique tag
        The idea is to create a unique 'Name' tag for each snapshot which can be used to find the snapshot later
        The 'Name' tag will be used in DSCC as backup 'name'
        The method does not handle the condition of returning a list of snapshots if more than one snapshot contains
        the provided tag

        Args:
            tag (Tag): Tag object

        Returns:
            _type_: Returns a EC2 snapshot 'resource' object if it contains the provided tag
        """
        snapshots = self.ec2_resource.snapshots.filter(OwnerIds=["self"])
        logger.info(f"Snapshots {snapshots}")

        for snapshot in snapshots:
            if snapshot.tags and dict(tag) in snapshot.tags:
                logger.info(f"Snapshot found with tag {tag} is {snapshot}")
                return snapshot

        return None

    def set_snapshot_tags(self, snapshot_id: str, tags_list: list[Tag]):
        snapshot = self.get_snapshot_by_id(snapshot_id=snapshot_id)
        logger.info(f"Snapshot = {snapshot}")

        tags_dict = [dict(tag) for tag in tags_list]
        tags = snapshot.create_tags(Tags=tags_dict)
        logger.info(f" ------ {tags} ----- ")

    def filter_ebs_snapshots_by_tag(self, tag_name: str, tag_values: list[str]):
        snapshots = self.ec2_resource.snapshots.filter(Filters=[{"Name": f"tag:{tag_name}", "Values": tag_values}])
        for snapshot in snapshots:
            logger.info(f" ----- Snapshot ID: {snapshot.id} ----- ")

        return snapshots
