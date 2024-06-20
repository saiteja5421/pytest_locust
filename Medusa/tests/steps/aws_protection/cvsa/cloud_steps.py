import datetime
import logging
import math
import os
import re
import time
from os import getenv
from typing import List

from assertpy import assert_that
from azure.core.exceptions import ResourceNotFoundError
from pytest_check import check
from waiting import wait, TimeoutExpired

from lib.common.enums.aws_region_zone import AWSRegionZone
from lib.common.enums.az_regions import AZRegion
from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.common.enums.cvsa import CvsaType, CloudProvider, CloudRegions, AzureRegions
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_allowed_instances import (
    is_allowed,
    get_instance_details_by_name,
)
from lib.platform.aws_boto3.models.instance import Tag
from botocore.exceptions import ClientError
from lib.platform.cloud.cloud_dataclasses import CloudInstanceState, CloudImage, CloudInstance, CloudDisk
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.functional.aws_protection.cvsa_manager.constants import regions

logger = logging.getLogger()


def get_creator_environment_name() -> str:
    cluster_name = getenv("CLUSTER_NAME")
    cluster_region = getenv("CLUSTER_REGION")
    creator_environment_name = getenv("CREATOR_ENVIRONMENT_NAME")
    if cluster_region and cluster_name:
        return f"{cluster_name}-{cluster_region}"
    elif creator_environment_name:
        return creator_environment_name
    else:
        return "localstack"


def get_arn_role() -> str:
    creator_environment_name = get_creator_environment_name()
    account_id = os.getenv("AWS_ACCOUNT_ID")
    if account_id and creator_environment_name:
        return f"arn:aws:iam::{account_id}:role/hpe-cvsa-manager-{creator_environment_name}"
    else:
        return os.getenv("TEST_AWS_ROLE_ARN")


def get_instance_state(cloud_vm_mgr: CloudVmManager, instance_id: str) -> CloudInstanceState:
    try:
        state = cloud_vm_mgr.get_instance(instance_id).state
        logger.info(f"Verifying termination of instance: {instance_id}, state={state}")
    except ResourceNotFoundError:
        return CloudInstanceState.UNKNOWN
    return state


def verify_instance_terminated(cloud_vm_mgr: CloudVmManager, instance_id: str):
    wait(
        lambda: get_instance_state(cloud_vm_mgr, instance_id)
        in [CloudInstanceState.TERMINATED, CloudInstanceState.UNKNOWN],
        timeout_seconds=300,
        sleep_seconds=5,
    )
    logger.info(f"Instance is terminated: {instance_id}")


def verify_volume_deleted(cloud_vm_mgr: CloudVmManager, volume_id: str):
    assert cloud_vm_mgr.get_disk(volume_id) is None, f"Volume {volume_id} expected to be deleted but it still exists"
    logger.info(f"Verified that volume {volume_id} is deleted")


def verify_instance_running(cloud_vm_mgr: CloudVmManager, instance_id: str):
    wait(
        lambda: get_instance_state(cloud_vm_mgr, instance_id) == CloudInstanceState.RUNNING,
        timeout_seconds=300,
        sleep_seconds=5,
    )
    logger.info(f"Instance is running: {instance_id}")


def verify_instance_exists(cloud_vm_mgr: CloudVmManager, instance_id: str):
    wait(
        lambda: get_instance_state(cloud_vm_mgr, instance_id) in CloudInstanceState.list(),
        timeout_seconds=300,
        sleep_seconds=5,
    )
    logger.info(f"Instance exists: {instance_id} with state {get_instance_state(cloud_vm_mgr, instance_id)}")


def wait_for_instance_to_be_deployed(cloud_vm_mgr: CloudVmManager, cam_account_id: str):
    tag = Tag(Key="cvsa-cloud-account-manager-account-id", Value=cam_account_id)
    logger.info(f"Waiting for instance for cam_account_id: {cam_account_id}")
    wait(
        lambda: len(cloud_vm_mgr.list_instances(tags=[tag])) == 1,
        timeout_seconds=120,
        sleep_seconds=1,
    )
    logger.info(f"Found instance for cam_account_id: {cam_account_id}")
    logger.info(f"Waiting for instance to be in running state for cam_account_id: {cam_account_id}")
    # We need to wait around 3 minutes after start to be able to stop instance
    time.sleep(180)


def get_amis_for_update(cloud_vm_mgr: CloudVmManager) -> List[CloudImage]:
    ami_version_to_amis = {}
    for ami in get_all_amis_for_environment(cloud_vm_mgr):
        ami.version = _parse_ami_version(ami.name)
        if ami.version != "0.0":
            ami_version_to_amis[ami.version] = ami
    ami_versions = sorted(ami_version_to_amis.keys())
    assert len(ami_versions) >= 2, f"There aren't enough AMIs for an update. Available image is {ami_version_to_amis}"
    ami_version_old, ami_version_latest = ami_versions[-2:]
    return [ami_version_to_amis[ami_version_old], ami_version_to_amis[ami_version_latest]]


def get_storeonce_ip(cloud_vm_mgr: CloudVmManager, cvsa_id: str) -> str:
    logger.info(f"Get storeonce ip, cvsa id:{cvsa_id}")
    instance = get_instance_by_cvsa_id(cloud_vm_mgr, cvsa_id)
    ip = instance.public_ip
    logger.info(f"Cvsa instance {instance}, ip:{ip}")
    return ip


def turn_off_cvsa_instance(cloud_vm_mgr: CloudVmManager, customer_id: str):
    logger.info(f"Turn off cvsa instance, customer id:{customer_id}")
    tag = Tag(Key="cvsa-application-customer-id", Value=customer_id)
    instances = cloud_vm_mgr.list_instances(tags=[tag])
    logger.info(f"Customer: {customer_id}, instances: {instances}")
    assert len(instances) == 1
    cloud_vm_mgr.stop_instance(instances[0].id)
    verify_instance_state(cloud_vm_mgr, customer_id, CloudInstanceState.STOPPED)
    logger.info(f"Cvsa instance {instances[0]} stopped. Customer: {customer_id}")


def turn_on_cvsa_instance(cloud_vm_mgr: CloudVmManager, customer_id: str):
    logger.info(f"Turn on cvsa instance, customer id:{customer_id}")
    tag = Tag(Key="cvsa-application-customer-id", Value=customer_id)
    instances = cloud_vm_mgr.list_instances(tags=[tag])
    logger.info(f"Customer: {customer_id}, instances: {instances}")
    assert len(instances) == 1
    cloud_vm_mgr.start_instance(instances[0].id)
    verify_instance_state(cloud_vm_mgr, customer_id, CloudInstanceState.RUNNING)
    cloud_vm_mgr.wait_cloud_instance_status_ok(instance_id=instances[0].id)
    logger.info(f"Cvsa instance {instances[0]} running. Customer: {customer_id}")


def verify_instance_state(
    cloud_vm_mgr: CloudVmManager,
    cvsa_id: str,
    state: CloudInstanceState,
    timeout_seconds: int = 120,
):
    logger.info(f"Verify cvsa instance, cvsa id:{cvsa_id}, has state {state}")
    tag = Tag(Key="cvsa-id", Value=cvsa_id)
    instances = cloud_vm_mgr.list_instances(tags=[tag])
    logger.info(f"Cvsa-id: {cvsa_id}, instances: {instances}")
    for instance in instances:
        logger.info(f"Checking instance {instance}")
        if instance.state != CloudInstanceState.TERMINATED or state == CloudInstanceState.TERMINATED:
            wait(
                lambda: cloud_vm_mgr.get_instance(instance.id).state == state,
                timeout_seconds=timeout_seconds,
                sleep_seconds=5,
            )
            logger.info(f"Cvsa instance {instance} has state {state}. Cvsa-id: {cvsa_id}")


def get_instance_by_cvsa_id(
    cloud_vm_mgr: CloudVmManager,
    cvsa_id: str,
) -> CloudInstance:
    tag = Tag(Key="cvsa-id", Value=cvsa_id)
    instances = cloud_vm_mgr.list_instances(tags=[tag], states=CloudInstanceState.list_not_terminated())
    logger.info(f"Cvsa: {cvsa_id}, instances: {instances}")
    assert len(instances) == 1
    return instances[0]


def get_data_volume(
    cloud_vm_mgr: CloudVmManager,
    cvsa_id: str,
) -> CloudDisk:
    instance = get_instance_by_cvsa_id(cloud_vm_mgr, cvsa_id)
    volumes = instance.data_disks
    logger.info(f"Cvsa: {cvsa_id}, volumes: {volumes}")

    def _find_data_volume():
        devices = ["/dev/sdb", "DataVolume"]
        _volume_data = next(filter(lambda vol: vol.device in devices, volumes))
        if _volume_data:
            return _volume_data

    try:
        logger.info("Searching for volumes:")
        cloud_data = wait(_find_data_volume, timeout_seconds=600, sleep_seconds=5)
        logger.info(f"Volume found: {cloud_data}")
        return cloud_data
    except TimeoutExpired:
        raise AssertionError("Failed to find data volume")


def verify_instance_type_and_volume_size(
    cloud_vm_mgr: CloudVmManager,
    cvsa_id: str,
    instance_details=CloudInstanceDetails.R6I_LARGE,
    volume_size_bytes=50_000_000_000,
    strict_instance_details: bool = False,
):
    instance_type = instance_details.value.instance_type
    logger.info("Start verifying instance type and volume data size")

    instance = get_instance_by_cvsa_id(cloud_vm_mgr, cvsa_id)
    cloud_data = get_data_volume(cloud_vm_mgr, cvsa_id)

    if instance_type == instance.instance_type:
        assert instance_type == instance.instance_type, f"expected: {instance_type}, actual: {instance.instance_type}"
    else:
        logger.error(
            f"Given instance type not match requested instance type. Given: {instance_type},"
            f" Requested: {instance_details.value.instance_type}"
        )
        given_instance = get_instance_details_by_name(instance_type)
        assert is_allowed(
            instance_details, given_instance, strict_instance_details
        ), f"Instance is to big, wanted: {instance_details}, given: {given_instance}"
    with check:
        is_size_in_tolerance = math.isclose(volume_size_bytes, cloud_data.disk_size_bytes, abs_tol=537_000_000)
        description = (
            f"volume_size_bytes exceeded the 537MB tolerance. "
            f"Expected bytes: {volume_size_bytes}, got: {cloud_data.disk_size_bytes}. Instance: {instance}"
        )
        assert_that(is_size_in_tolerance, description).is_true()
    logger.info("Verifying instance type and data volume size finished")


def verify_not_deployed_cvsa(cloud_vm_mgr: CloudVmManager, account_id: str):
    logger.info(f"Searching  cvsa instances with account id: {account_id}")
    tag = Tag(Key="cvsa-application-customer-id", Value=account_id)
    instances = cloud_vm_mgr.list_instances(tags=[tag])
    logger.info(f"Found cvsa instances: {instances}")
    assert len(instances) == 0, f"Instances should be 0, got: {instances}, account id: {account_id}"


def verify_deployed_cvsa(
    cloud_vm_mgr: CloudVmManager,
    cvsa_id: str,
    ami_version=None,
    disaster_recovery=False,
    cvsa_type=CvsaType.BACKUP,
):
    logger.info("Start verifying cvsa")
    logger.info(f"Searching deployed cvsa instances, cvsa: {cvsa_id}")
    tag = Tag(Key="cvsa-id", Value=cvsa_id)
    instances = cloud_vm_mgr.list_instances(tags=[tag], states=CloudInstanceState.list_not_terminated())
    logger.info(f"Found cvsa instances: {instances}")
    if disaster_recovery:
        running_instances = [instance for instance in instances if instance.state == CloudInstanceState.RUNNING]
        assert len(running_instances) == 1, f"Expected one running instance with given cvsa_id, got: {instances}"
        instances = running_instances
    else:
        assert len(instances) == 1, f"Expected one instance, got: {instances}"
    instance = instances[0]
    volume = instance.data_disks[0]
    cvsa_id_tag = next(filter(lambda id_tag: id_tag.Key == "cvsa-id", instance.tags))
    cvsa_type_tag = next(filter(lambda id_tag: id_tag.Key == "cvsa-type", instance.tags))

    assert instance.state == CloudInstanceState.RUNNING, f"State is different than running: {instance.state}"
    assert cvsa_type.value == cvsa_type_tag.Value, f"{cvsa_type.value} != {cvsa_type_tag.Value}"

    logger.info(f"Starting volume verification: {volume}")
    assert volume is not None
    assert volume.state.lower() == "attached", f"Volume not attached: {volume}, state: {volume.state}"
    assert volume.instance_id == instance.id
    assert tag in volume.tags
    assert cvsa_id_tag in volume.tags
    logger.info(f"Finished volume verification: {volume}")

    logger.info(f"Found subnets: {instance.subnets}")
    assert instance.public_ip is not None
    assert len(instance.subnets) == 1
    if instance.cloud_provider == CloudProvider.AWS:
        assert_that(instance.subnets[0].tags).contains(allocated_by_tag())
    logger.info(f"Finished subnet verification: {instance.subnets}")
    logger.info("Finished cvsa verification")
    if ami_version is None:
        verify_newest_ami(cloud_vm_mgr, cvsa_id)
    else:
        assert get_cvsa_version(cloud_vm_mgr, cvsa_id) == ami_version
    if get_creator_environment_name() != "localstack" and instance.cloud_provider == CloudProvider.AWS:
        instance_metadata_state = cloud_vm_mgr.get_instance_metadata_ec2_tags_enabled(instance.id)
        assert instance_metadata_state, "Instance metadata tags are not enabled"


def allocated_by_tag(cloud_provider: CloudProvider = CloudProvider.AWS) -> Tag:
    environment = get_creator_environment_name()
    if getenv("LOCAL_ENV", "False").lower() == "true" and environment != "localstack":
        value = "atlantia-cvsa-manager"
    else:
        value = f"atlantia-cvsa-manager-{environment}"
    logger.info(f"Subnet tag is: {value}")
    if cloud_provider is not CloudProvider.AWS:
        return Tag(Key="managed-by", Value=value)
    else:
        return Tag(Key="allocated-by", Value=value)


def get_default_region(cloud_provider: CloudProvider) -> CloudRegions:
    if cloud_provider == CloudProvider.AWS:
        return regions.get(getenv("AWS_REGION_ONE", AWSRegionZone.EU_WEST_1.value))
    if cloud_provider == CloudProvider.AZURE:
        return getenv("AZURE_REGION_ONE", AzureRegions.AZURE_CENTRALUS)
    else:
        raise AttributeError(f"Wrong cloud_provider provided: {cloud_provider}")


def get_default_region_str(cloud_provider: CloudProvider) -> CloudRegions:
    if cloud_provider == CloudProvider.AWS:
        return getenv("AWS_REGION_ONE", AWSRegionZone.EU_WEST_1)
    if cloud_provider == CloudProvider.AZURE:
        return getenv("AZURE_REGION_ONE", AZRegion.CENTRAL_US)
    else:
        raise AttributeError(f"Wrong cloud_provider provided: {cloud_provider}")


def get_default_instance(cloud_provider: CloudProvider) -> CloudInstanceDetails:
    if cloud_provider == CloudProvider.AWS:
        return CloudInstanceDetails.R6I_LARGE
    if cloud_provider == CloudProvider.AZURE:
        return CloudInstanceDetails.Standard_E2S_v5
    else:
        raise AttributeError(f"Wrong cloud_provider provided: {cloud_provider}")


def verify_newest_ami(cloud_vm_mgr: CloudVmManager, cvsa_id: str):
    logger.info("Check if AMI version is the newest")
    valid_amis = get_all_amis_for_environment(cloud_vm_mgr)
    newest_ver = "0.0"
    for valid_ami in valid_amis:
        ver = _parse_ami_version(valid_ami.name)
        newest_ver = ver if newest_ver < ver else newest_ver
    cvsa_version = get_cvsa_version(cloud_vm_mgr, cvsa_id)
    assert cvsa_version == newest_ver
    logger.info(f"AMI version is the newest: {cvsa_version}")


def get_all_amis_for_environment(cloud_vm_mgr: CloudVmManager) -> List[CloudImage]:
    environment = get_creator_environment_name()
    logger.info(f"Looking for amis on {environment}")
    tag = Tag(Key=f"env:{environment}", Value="true")
    images = [valid_ami for valid_ami in cloud_vm_mgr.list_images() if valid_ami.tags and tag in valid_ami.tags]
    logger.info(f"Found images: {images}")
    assert len(images) > 0, f"Not found images for environment: {environment}"
    return images


def get_cvsa_private_ip(kafka: KafkaManager, cloud_vm_mgr: CloudVmManager) -> str:
    tag = Tag(Key="cvsa-cloud-account-manager-account-id", Value=kafka.cam_account_id)
    logger.info(f"Obtaining cVSA Private IP for customer {tag}")
    instances = cloud_vm_mgr.list_instances(tags=[tag], states=CloudInstanceState.list_not_terminated())
    private_ip = instances[0].private_ip
    assert private_ip, f"Private IP not found for instance: {instances[0]}"
    logger.info(f"cVSA Private IP: {private_ip}")
    return private_ip


def _parse_ami_version(ami_name):
    image_prefix = os.getenv("IMAGE_NAME_PREFIX", "atlantia-cvsa-v")
    pattern = re.compile(image_prefix + r"(\d+\.\d+\.\d+)(?:-(\d+\.\d+))?")
    match = pattern.search(ami_name)
    if match:
        version = match.group(1)
        sub_version = match.group(2)
        return version if not sub_version else f"{version}-{sub_version}"
    else:
        logger.info(f"Can't parse AMI name: {ami_name}")
        return "0.0"


def get_cvsa_version(cloud_vm_mgr: CloudVmManager, cvsa_id: str) -> str:
    logger.info(f"Obtaining cVSA version for customer {cvsa_id}")
    instance = get_instance_by_cvsa_id(cloud_vm_mgr, cvsa_id)
    ami_name = instance.image.name
    logger.info(f"Instance {instance} ami name: {ami_name}")
    assert ami_name, "AMI not found"
    cvsa_version = _parse_ami_version(ami_name)
    return cvsa_version


def create_orphaned_instance(kafka_mgr: KafkaManager, cloud_vm_mgr: CloudVmManager) -> CloudInstance:
    # Create the orphaned (because it will exist only in the cloud,
    # without entry in the cvsa-manager's database) instance
    _, latest_ami = get_amis_for_update(cloud_vm_mgr=cloud_vm_mgr)
    env = get_creator_environment_name()
    instance = cloud_vm_mgr.create_instance(
        image_id=latest_ami.id,
        tags=[
            Tag(Key="created", Value=datetime.datetime.now(datetime.timezone.utc).isoformat()),
            Tag(Key="cvsa-id", Value=kafka_mgr.cvsa_id),
            Tag(Key="cvsa-application-customer-id", Value=kafka_mgr.account_id),
            Tag(Key="cvsa-cloud-account-manager-account-id", Value=kafka_mgr.cam_account_id),
            Tag(Key="cvsa-creator-environment", Value=env),
            Tag(Key="cvsa-terminate-confirmation", Value="true"),
        ],
        subnet_tag=allocated_by_tag(cloud_provider=cloud_vm_mgr.name()),
        instance_type=get_default_instance(cloud_provider=cloud_vm_mgr.name()).value.instance_type,
        location=get_default_region_str(cloud_vm_mgr.name()),
    )
    return instance
