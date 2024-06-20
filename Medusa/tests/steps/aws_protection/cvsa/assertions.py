import logging
import math
from datetime import datetime
from typing import List

from assertpy import assert_that
from azure.core.exceptions import ResourceNotFoundError
from pytest_check import check
from waiting import wait

from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.common.enums.cvsa import CloudProvider
from lib.platform.aws_boto3.models.instance import Tag
from lib.platform.aws_boto3.s3_manager import S3Manager
from lib.platform.cloud.cloud_dataclasses import CloudInstanceState, CloudDisk, CloudInstance, CloudSubnet
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.functional.aws_protection.cvsa_manager.constants import (
    get_grpc_cloud_object_store_service_stub,
)
from tests.steps.aws_protection.cvsa.cloud_steps import get_creator_environment_name, _parse_ami_version
from tests.steps.aws_protection.cvsa.grpc_steps import get_object_stores_by_cvsa_id

# 0.5 GiB because AWS input requires providing GiBs as integer
TOLERANCE_BYTES = 537_000_000


@check.check_func
def assert_cvsa_tags_values_and_presence(kafka_mgr: KafkaManager, cloud_vm_mgr: CloudVmManager):
    instance = cloud_vm_mgr.list_instances(tags=[Tag(Key="cvsa-id", Value=kafka_mgr.cvsa_id)])[0]

    check_values_tags = [
        Tag(Key="cvsa-application-customer-id", Value=kafka_mgr.account_id),
        Tag(Key="cvsa-cloud-account-manager-account-id", Value=kafka_mgr.cam_account_id),
        Tag(Key="cvsa-cloud-service-provider-account-id", Value=kafka_mgr.csp_account_id),
        Tag(Key="cvsa-creator-environment", Value=get_creator_environment_name()),
        Tag(Key="cvsa-id", Value=kafka_mgr.cvsa_id),
    ]
    check_values_presence = ["cvsa-is-read-only", "cvsa-requester", "cvsa-serial-number", "cvsa-type"]
    instance_tag_keys = [tag.Key for tag in instance.tags]

    logging.debug(f"Assert following cvsa tags values: {check_values_tags} in vm: {instance.id}")
    logging.debug(f"Assert following cvsa tags presence: {check_values_presence} in vm: {instance.id}")

    assert_that(instance.tags).contains(*check_values_tags)
    assert_that(instance_tag_keys).contains(*check_values_presence)


def assert_one_cvsa_created(kafka_mgr: KafkaManager, cloud_vm_mgr: CloudVmManager) -> CloudInstance:
    vms = cloud_vm_mgr.list_instances(tags=[Tag(Key="cvsa-id", Value=kafka_mgr.cvsa_id)])
    description = f"Expected number of VMs with the same cVSA ID is exactly 1. Found: {[vm.id for vm in vms]}."
    logging.debug(f"Assert one cvsa created, {description}")

    assert_that(vms, description=description).is_length(1)
    return vms[0]


@check.check_func
def assert_one_cvsa_running(kafka_mgr: KafkaManager, cloud_vm_mgr: CloudVmManager):
    vms = cloud_vm_mgr.list_instances(
        tags=[Tag(Key="cvsa-id", Value=kafka_mgr.cvsa_id)], states=CloudInstanceState.list_not_terminated()
    )
    description = f"Expected number of running VMs with the same cVSA ID is exactly 1. Found: {[vm.id for vm in vms]}."
    assert_that(vms, description=description).is_length(1)


@check.check_func
def assert_cvsa_does_not_exist(kafka_mgr: KafkaManager, cloud_vm_mgr: CloudVmManager):
    tag = Tag(Key="cvsa-id", Value=kafka_mgr.cvsa_id)
    logging.debug(f"Assert cvsa does not exist with following tag: {tag}")
    wait(
        lambda: cloud_vm_mgr.list_instances(tags=[tag], states=CloudInstanceState.list_not_terminated()) == [],
        timeout_seconds=300,
        sleep_seconds=10,
        waiting_for=f"Expected number of VMs with the same cVSA ID is exactly 0,"
        f"Got: {cloud_vm_mgr.list_instances(tags=[tag])}",
    )


@check.check_func
def assert_cvsa_type(kafka_mgr: KafkaManager, cloud_vm_mgr: CloudVmManager, expected_cvsa: CloudInstanceDetails):
    instance = cloud_vm_mgr.list_instances(tags=[Tag(Key="cvsa-id", Value=kafka_mgr.cvsa_id)])[0]
    assert_that(instance.instance_type).is_equal_to(expected_cvsa.value.instance_type)


@check.check_func
def assert_one_disk_attached(kafka_mgr: KafkaManager, cloud_vm_mgr: CloudVmManager):
    instance = cloud_vm_mgr.list_instances(tags=[Tag(Key="cvsa-id", Value=kafka_mgr.cvsa_id)])[0]
    assert_that(instance.data_disks).is_length(1)


def custom_sort_key(version_str: str):
    if version_str == "0.0":
        return tuple(map(int, "0"))
    version_parts = version_str.split("-")
    main_version = version_parts[0].split(".")
    if len(version_parts) > 1:
        sub_version = version_parts[1].split(".")
        return tuple(map(int, main_version + sub_version))
    else:
        return tuple(map(int, main_version))


@check.check_func
def assert_last_image_version_used(kafka_mgr: KafkaManager, cloud_vm_mgr: CloudVmManager):
    instance = cloud_vm_mgr.list_instances(tags=[Tag(Key="cvsa-id", Value=kafka_mgr.cvsa_id)])[0]
    used_image_version = _parse_ami_version(instance.image.name)
    images_list = cloud_vm_mgr.list_images()
    cvsa_versions_list = [
        _parse_ami_version(tag.Value)
        for image in images_list
        for tag in image.tags
        if tag.Key in ["FullName", "Name"] and tag.Value
    ]
    cvsa_versions_list = sorted(cvsa_versions_list, key=custom_sort_key, reverse=True)
    assert_that(used_image_version).is_equal_to(cvsa_versions_list[0])


@check.check_func
def assert_object_store_count(cvsa_id: str, count: int):
    service_stub = get_grpc_cloud_object_store_service_stub()
    object_stores = get_object_stores_by_cvsa_id(service_stub=service_stub, cvsa_id=cvsa_id)
    logging.info(f"Found object stores are: {object_stores} with items {object_stores.items}, expected length: {count}")
    assert_that(object_stores.items).is_length(count)


@check.check_func
def assert_disk_size(kafka_mgr: KafkaManager, cloud_vm_mgr: CloudVmManager, expected_disk_size_bytes: int):
    instance = cloud_vm_mgr.list_instances(tags=[Tag(Key="cvsa-id", Value=kafka_mgr.cvsa_id)])[0]
    assert_that(instance.data_disks).is_true()
    disk_size = instance.data_disks[0].disk_size_bytes
    assert_volume_bytes_size(disk_size, expected_disk_size_bytes)


@check.check_func
def assert_volume_bytes_size(message_size_bytes: int, volume_size_bytes: int):
    is_size_in_tolerance = math.isclose(message_size_bytes, int(volume_size_bytes), abs_tol=TOLERANCE_BYTES)
    description = f"{message_size_bytes} != {int(volume_size_bytes)} above tolerance={TOLERANCE_BYTES}"
    assert_that(is_size_in_tolerance, description=description).is_true()


@check.check_func
def assert_volumes_deleted(cloud_vm_mgr: CloudVmManager, volumes: List[CloudDisk]):
    def check_all_volumes_deleted(vs):
        result = True
        for v in vs:
            if cloud_vm_mgr.get_disk(disk_id=v.name) is not None:
                logging.info(f"Verifying deletion of volume: {v.name}, it should be deleted but still exists")
                result = False
        return result

    wait(lambda: check_all_volumes_deleted(volumes), timeout_seconds=300, sleep_seconds=5)


@check.check_func
def assert_nic_deleted(cloud_vm_mgr: CloudVmManager, vm_subnets: list[CloudSubnet]):
    if cloud_vm_mgr.name() != CloudProvider.AZURE:
        return
    for subnet in vm_subnets:
        try:
            nic_id = subnet.id
            cloud_vm_mgr.get_network_interface(nic_id)
        except ResourceNotFoundError:
            pass


@check.check_func
def assert_ip_deleted(cloud_vm_mgr: CloudVmManager, ip_addr: str):
    if cloud_vm_mgr.name() != CloudProvider.AZURE:
        return
    for ip_obj in cloud_vm_mgr.list_all_ip_objects():
        if ip_obj.ip_address == ip_addr:
            raise AssertionError(f"PublicIPAddress object with IP: {ip_addr} still exists: {ip_obj.as_dict()}")


@check.check_func
def assert_batch_logs_created(s3: S3Manager, correlation_id: str):
    current_date = datetime.now().strftime("%Y-%m-%d")
    s3_name = f"hpe-cvsa-manager-reports-{get_creator_environment_name()}"
    bucket = s3.get_s3_bucket(s3_name)
    wait(
        lambda: [
            log for log in bucket.objects.filter(Prefix=f"batchperformance/{current_date}/{correlation_id}.json").all()
        ],
        timeout_seconds=1800,
        sleep_seconds=10,
        waiting_for=f"File {s3_name}/batchperformance/{current_date}/{correlation_id}.json doest not exists after 30 minutes.",
    )
