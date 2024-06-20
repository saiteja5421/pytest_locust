"""
TC30: Remove cVSA Instance with all resources.
    Send cVSARequestedEvent
    Check cVSACreatedEvent
    Send deregistration event to CAM topic
    Verify that ec2 and volumes are terminated.
    Verify that s3 is deleted (if possible, check with CAM).
    Verify vault is cleaned from customer data
"""

from pytest import fixture, mark

from lib.common.enums.cvsa import VaultCredentialType
from lib.platform.aws_boto3.s3_manager import S3Manager
from lib.platform.cloud.cloud_vm_manager import CloudVmManager, cloud_vm_managers_names
from lib.platform.kafka.kafka_manager import KafkaManager, TopicEncoding
from lib.platform.storeonce.storeonce import StoreOnce
from tests.steps.aws_protection.cvsa.assertions import assert_batch_logs_created
from tests.steps.aws_protection.cvsa.cloud_steps import get_storeonce_ip
from tests.steps.aws_protection.cvsa.common_steps import cleanup_cvsa_instance
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    send_finished_event,
    verify_finished_event,
    create_new_cvsa_instance_and_validate,
)
from tests.steps.aws_protection.cvsa.kafka_steps import verify_deleted_event
from tests.steps.aws_protection.cvsa.vault_steps import get_cvsa_credentials


@fixture(scope="function")
def reports_kafka_mgr(kafka_mgr):
    reports_kafka = KafkaManager(
        "atlas.reports.events", tc_id=30, topic_encoding=TopicEncoding.NONE, account_id=kafka_mgr.account_id
    )
    return reports_kafka


@mark.order(3000)
@mark.cvsa_aws
@mark.cvsa_azure
@mark.cvsa_cloud
@mark.parametrize("cloud_vm_mgr", cloud_vm_managers_names())
def test_tc30(
    kafka_mgr: KafkaManager, reports_kafka_mgr: KafkaManager, cloud_vm_mgr: CloudVmManager, request, aws_s3: S3Manager
):
    cloud_vm_mgr = request.getfixturevalue(cloud_vm_mgr)
    cvsa_model = create_new_cvsa_instance_and_validate(
        cloud_vm_mgr=cloud_vm_mgr, kafka_mgr=kafka_mgr, data_protected_gb=1
    )
    send_finished_event(kafka_mgr, cloud_provider=cloud_vm_mgr.name())
    verify_finished_event(kafka_mgr, cloud_provider=cloud_vm_mgr.name())
    credentials = get_cvsa_credentials(kafka_mgr.cvsa_id, VaultCredentialType.ADMIN)
    storeonce = StoreOnce(get_storeonce_ip(cloud_vm_mgr, kafka_mgr.cvsa_id), credentials.username, credentials.password)
    cloud_store_id = storeonce.get_cloud_store().cloud_store_details.cloud_store_id
    cleanup_cvsa_instance(kafka_mgr, cloud_vm_mgr, post_cleanup=False)
    verify_deleted_event(
        kafka_mgr, reports_kafka_mgr, cloud_store_id, cvsa_model.catalyst_store, cloud_provider=cloud_vm_mgr.name()
    )

    assert_batch_logs_created(aws_s3, correlation_id=kafka_mgr.correlation_id.decode("utf-8"))
