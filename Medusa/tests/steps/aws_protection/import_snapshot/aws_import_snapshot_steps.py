"""
This module contains functions related to performing operations on improted AMI and Snapshots from AWS
"""
import logging
from datetime import datetime

from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.aws_boto3.models.instance import Tag

logger = logging.getLogger()


def get_volume_snapshot_point_in_time(aws: AWS, snapshot_id: str) -> str:
    """Returns volume snapshot created time in DSCC supported format 'point_in_time' in DSCC is equal to the creation time in AWS

    Args:
        aws (AWS): AWSFactory object
        snapshot_id (str): AWS volume snapshot ID

    Returns:
        str: point_in_time in DSCC format
    """
    snapshot = aws.ebs.get_snapshot_by_id(snapshot_id=snapshot_id)
    created_time: datetime = snapshot.start_time
    logger.info(f"Snapshot {snapshot} was created at {created_time}")

    point_in_time: str = created_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    logger.info(f"{point_in_time}= for Snapshot {snapshot_id}")
    return point_in_time


def get_ec2_ami_point_in_time(aws: AWS, ami_id: str) -> str:
    """Returns AMI created time in DSCC supported format 'point_in_time' in DSCC is equal to the creation time in AWS

    Args:
        aws (AWS): AWSFactory object
        ami_id (str): AWS AMI ID

    Returns:
        str: point_in_time in DSCC format
    """
    ami = aws.ec2.get_ami_by_id(ami_id=ami_id)
    created_date: datetime.datetime = ami.creation_date  # Returned in this format -> 2023-04-11T19:35:25.000Z
    logger.info(f"AMI {ami} was created at {created_date}")

    logger.info(f"Converting string {created_date} into datetime object")
    created_date_object = datetime.strptime(created_date, "%Y-%m-%dT%H:%M:%S.%fZ")
    logger.info(created_date_object)

    logger.info("Removing milliseconds from the created time to match DSCC format")
    point_in_time: str = created_date_object.strftime("%Y-%m-%dT%H:%M:%SZ")
    logger.info(f"{point_in_time}= for AMI {ami_id}")
    return point_in_time


def verify_imported_snapshot_tags(aws: AWS, snapshot_id: str, tags: list[Tag]):
    """Checks provided tags' presence in the requested Snapshot

    Args:
        aws (AWS): AWSFactory object
        snapshot_id (str): Snapshot against which tags need to be checked
        tags (list[Tag]): list of tags expected 'to be present' on the Snapshot
    """
    unavailable_tags_list: list[Tag] = []
    snapshot = aws.ebs.get_snapshot_by_id(snapshot_id=snapshot_id)
    logger.info(f"Snapshot tags {snapshot.tags}")

    for tag in tags:
        if dict(tag) not in snapshot.tags:
            unavailable_tags_list.append(tag)

    assert len(unavailable_tags_list) == 0, f"Snapshot Tags {snapshot.tags}, unavailable tags {unavailable_tags_list}"


def verify_imported_ami_tags(aws: AWS, ami_id: str, tags: list[Tag]):
    """Checks provided tags' presence in the requested AMI

    Args:
        aws (AWS): AWSFactory object
        ami_id (str): AMI against which tags need to be checked
        tags (list[Tag]): list of tags expected 'to be present' on the AMI
    """
    unavailable_tags_list: list[Tag] = []
    ami = aws.ec2.get_ami_by_id(ami_id=ami_id)
    logger.info(f"AMI tags {ami.tags}")

    for tag in tags:
        if dict(tag) not in ami.tags:
            unavailable_tags_list.append(tag)

    assert len(unavailable_tags_list) == 0, f"Snapshot Tags {ami.tags}, unavailable tags {unavailable_tags_list}"


def verify_tags_not_present_on_imported_snapshot(aws: AWS, snapshot_id: str, tags: list[Tag]):
    """Checks provided tags' presence in the requested Snapshot

    Args:
        aws (AWS): AWSFactory object
        snapshot_id (str): Snapshot against which tags need to be checked
        tags (list[Tag]): list of tags expected 'not to be present' on the Snapshot
    """
    available_tags_list: list[Tag] = []
    snapshot = aws.ebs.get_snapshot_by_id(snapshot_id=snapshot_id)
    logger.info(f"Snapshot tags {snapshot.tags}")

    for tag in tags:
        if snapshot.tags and dict(tag) in snapshot.tags:
            available_tags_list.append(tag)

    assert len(available_tags_list) == 0, f"Snapshot Tags {snapshot.tags}, available tags {available_tags_list}"


def verify_tags_not_present_on_imported_ami(aws: AWS, ami_id: str, tags: list[Tag]):
    """Checks provided tags' presence in the requested AMI

    Args:
        aws (AWS): AWSFactory object
        ami_id (str): AMI against which tags need to be checked
        tags (list[Tag]): list of tags expected 'not to be present' on the AMI
    """
    available_tags_list: list[Tag] = []
    ami = aws.ec2.get_ami_by_id(ami_id=ami_id)
    logger.info(f"AMI tags {ami.tags}")

    for tag in tags:
        if ami.tags and dict(tag) in ami.tags:
            available_tags_list.append(tag)

    assert len(available_tags_list) == 0, f"Snapshot Tags {ami.tags}, available tags {available_tags_list}"
