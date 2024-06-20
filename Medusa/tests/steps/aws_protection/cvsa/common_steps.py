import logging
from os import getenv

from azure.core.exceptions import ResourceNotFoundError

from lib.common.enums.cvsa import StopReason, TerminateReason
from lib.dscc.backup_recovery.aws_protection.cvsa.cvsa_exceptions import NotFoundException
from lib.platform.aws_boto3.models.instance import Tag
from lib.platform.cloud.cloud_dataclasses import CloudInstanceState
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager, TopicEncoding
from tests.steps.aws_protection.cvsa.assertions import (
    assert_cvsa_does_not_exist,
    assert_volumes_deleted,
    assert_ip_deleted,
    assert_nic_deleted,
)
from tests.steps.aws_protection.cvsa.cam_updates_kafka_steps import send_unregister_event, verify_unregister_event
from tests.steps.aws_protection.cvsa.cloud_steps import verify_instance_terminated
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_stopped_event,
    verify_terminated_event,
)
from tests.steps.aws_protection.cvsa.vault_steps import verify_deleted_cvsa_credentials

logger = logging.getLogger()


def get_max_parallel_ro_requests() -> int:
    return int(getenv("MAX_PARALLEL_RO_REQUESTS_PER_CUSTOMER_REGION", 3))


def cleanup_cvsa_instance(cvsa_kafka: KafkaManager, cloud_vm_mgr: CloudVmManager, post_cleanup=True):
    logger.info(f"{'Post ' * post_cleanup}Cleanup started")
    cam_updates_kafka = KafkaManager(topic="csp.cam.updates", topic_encoding=TopicEncoding.PROTOBUF)
    if cvsa_kafka.cvsa_id:
        tag = Tag(Key="cvsa-id", Value=cvsa_kafka.cvsa_id)
    else:
        tag = Tag(Key="cvsa-cloud-account-manager-account-id", Value=cvsa_kafka.cam_account_id)
    try:
        instance = cloud_vm_mgr.list_instances(tags=[tag], states=CloudInstanceState.list_not_terminated())[0]
        if not cvsa_kafka.cvsa_id:
            cvsa_kafka.cvsa_id = next((tag.Value for tag in instance.tags if tag.Key == "cvsa-id"), None)
    except (NotFoundException, IndexError, ResourceNotFoundError):
        logger.error("Unable to find cVSA ID for instance - sending Unregister Customer Event")
        send_unregister_event(cvsa_kafka, cam_updates_kafka)
        verify_unregister_event(cvsa_kafka, cam_updates_kafka)
        logger.error("Unable to find cVSA ID for instance - Post Cleanup finished")
        return
    send_unregister_event(cvsa_kafka, cam_updates_kafka)
    verify_unregister_event(cvsa_kafka, cam_updates_kafka)
    verify_stopped_event(cvsa_kafka, reason=StopReason.CUSTOMER_UNREGISTER)
    verify_terminated_event(cvsa_kafka, reason=TerminateReason.CUSTOMER_UNREGISTER)
    verify_instance_terminated(cloud_vm_mgr, instance.id)
    assert_volumes_deleted(cloud_vm_mgr, volumes=[*instance.data_disks, instance.os_disk])
    verify_deleted_cvsa_credentials(cvsa_id=cvsa_kafka.cvsa_id)
    assert_nic_deleted(cloud_vm_mgr=cloud_vm_mgr, vm_subnets=instance.subnets)
    assert_ip_deleted(cloud_vm_mgr=cloud_vm_mgr, ip_addr=instance.public_ip)
    assert_cvsa_does_not_exist(kafka_mgr=cvsa_kafka, cloud_vm_mgr=cloud_vm_mgr)
    logger.info(f"{'Post ' * post_cleanup}Cleanup finished")


def cleanup_cvsa_instances(cvsa_kafka: KafkaManager, cloud_vm_mgrs: [CloudVmManager]):
    for cloud_vm_mgr in cloud_vm_mgrs:
        cvsa_kafka.set_offset_last_send_to_latest()
        offsets = cvsa_kafka.get_offsets()
        cvsa_kafka.set_offsets(offsets)
        cleanup_cvsa_instance(cvsa_kafka, cloud_vm_mgr)
