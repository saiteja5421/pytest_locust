"""
TC80: Happy path for Azure Cloud
    1. Send and verify backup requested event
    2. Verify created event backup, started and ready event
    3. Assert one VM created
    4. Assert VM tags
    5. Send unregister event and assert VM is correctly removed
"""

import logging

from pytest import mark

from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.platform.azure.az_vm_manager import AZVMManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.assertions import (
    assert_cvsa_tags_values_and_presence,
    assert_one_cvsa_created,
    assert_cvsa_type,
    assert_disk_size,
    assert_one_disk_attached,
    assert_last_image_version_used,
)
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_created_event_backup,
    verify_started_event,
    send_finished_event,
    verify_finished_event,
    verify_ready_event,
)
from tests.steps.aws_protection.cvsa.storeonce_steps import verify_storeonce_system

logger = logging.getLogger()


@mark.cvsa_azure
@mark.parametrize(
    "volume_size, vm_type",
    [(50_465_865_728, CloudInstanceDetails.Standard_E2S_v5)],
)
def test_tc80(
    azure: AZVMManager,
    kafka_mgr: KafkaManager,
    volume_size,
    vm_type,
):
    cloud_provider = azure.name()

    send_backup_requested_event(kafka_mgr, data_protected_gb=1, cloud_provider=cloud_provider)
    verify_backup_requested_event(kafka_mgr, data_protected_gb=1, cloud_provider=cloud_provider)
    verify_created_event_backup(
        kafka_mgr,
        data_protected_gb=1,
        backup_streams=None,
        volume_size_bytes=volume_size,
        cloud_provider=cloud_provider,
    )
    verify_started_event(kafka_mgr)

    verify_ready_event(
        kafka_mgr,
        cloud_provider=cloud_provider,
        backup_streams=None,
        volume_size_bytes=volume_size,
    )

    assert_one_cvsa_created(kafka_mgr=kafka_mgr, cloud_vm_mgr=azure)
    assert_cvsa_tags_values_and_presence(kafka_mgr=kafka_mgr, cloud_vm_mgr=azure)
    assert_cvsa_type(kafka_mgr=kafka_mgr, cloud_vm_mgr=azure, expected_cvsa=vm_type)
    assert_one_disk_attached(kafka_mgr=kafka_mgr, cloud_vm_mgr=azure)
    assert_last_image_version_used(kafka_mgr=kafka_mgr, cloud_vm_mgr=azure)
    assert_disk_size(kafka_mgr=kafka_mgr, cloud_vm_mgr=azure, expected_disk_size_bytes=volume_size)
    verify_storeonce_system(kafka_mgr, azure)

    send_finished_event(kafka_mgr, cloud_provider=cloud_provider)
    verify_finished_event(kafka_mgr, cloud_provider=cloud_provider)
