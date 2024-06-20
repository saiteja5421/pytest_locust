"""
TC01: First-time backup/restore request. No existing cVSA Instance for customer in a region.
    1. Verify that customer has not yet deployed cVSA or remove it.
    2. Send cVSARequestedEvent (from Backup Service, or e2e Test suite QA - kafka client)
    3. Check cVSACreatedEvent (at this point catalyst is configured, cloudbank is created ).
    4. Check cVSAStartedEvent (at this point cVSA is in running state within AWS and monitoring is triggered)
    5. Check cVSAReadyEvent (At this point cVSA is ready)
    6. Validate Cloud compute resource created.
    7. Verify storeonce health status.
    8. Verify that S3 and EBS exists
    9. Verify that cloud bank exists on storeonce.
TC18: Validate cVSA health monitoring components state.
    Send cVSARequestedEvent (from Backup Service, or e2e Test suite QA - kafka client)
    Check storage overview, catalyst stores, appliance summary, local storage overview state, remote support status
TC31: Validate cVSA StoreOnce configuration
    Send cVSARequestedEvent
    Check cVSACreatedEvent
    Verify if System Info is set properly
    Verify if NTP Servers are set properly
    Verify if Plattform Customer Info is set properly
TC32: Validate subnet discovery
    Send cVSARequestedEvent
    Check cVSAReadyEvent
    Validate that Subnet is properly chosen by tag
TC43: New instance should always have the latest AMI version
    Prerequisites: At least three AMI images are available with different versions
    Verify cvsa instance after request event
    Verify that AMI image is correctly chosen
TC48: Verify store client is attach to cloudbank
    Prerequisite: Verify that customer has deployed cVSA
    Verify that cloud bank have one client assigned to it.
    Verify that client name is matching name from Vault.
    Verify that client have access set to true.
"""

import logging

from pytest import fixture, mark

from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager, TopicEncoding
from tests.functional.aws_protection.cvsa_manager.constants import CVSA_APPLICATION_CUSTOMER_ID, AWS_REGION_1_NAME
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    verify_backup_requested_event,
    send_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cloud_steps import verify_not_deployed_cvsa, verify_deployed_cvsa
from tests.steps.aws_protection.cvsa.common_steps import cleanup_cvsa_instance
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_started_event,
    verify_instance_type_and_volume_size,
    verify_ready_event,
    send_finished_event,
    verify_finished_event,
    verify_created_event_backup,
)
from tests.steps.aws_protection.cvsa.kafka import new_kafka_lifecycle_events
from tests.steps.aws_protection.cvsa.kafka_steps import verify_billing_event
from tests.steps.aws_protection.cvsa.storeonce_steps import (
    verify_cloud_stores,
    verify_storeonce_system,
    validate_cloud_store_data,
)
from tests.steps.aws_protection.cvsa.vault_steps import verify_vault_credentials
from tests.steps.aws_protection.cvsa.write_read_backup_steps import (
    write_data_to_cvsa_cloud_store,
)


@fixture(scope="function")
def kafka_mgr(aws: CloudVmManager):
    kafka_mgr = new_kafka_lifecycle_events(tc_id=1, account_id=CVSA_APPLICATION_CUSTOMER_ID)
    yield kafka_mgr
    logger = logging.getLogger()
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)
    logger.info(10 * "=" + "Initiating Teardown" + 10 * "=")
    cleanup_cvsa_instance(kafka_mgr, aws)
    logger.info(10 * "=" + "Teardown Complete !!!" + 10 * "=")
    # cleanup_write_read_assets(kafka_mgr, aws)


@fixture(scope="function")
def billing_kafka(kafka_mgr):
    return KafkaManager(
        "atlas.reports.events",
        tc_id=1,
        account_id=kafka_mgr.account_id,
        topic_encoding=TopicEncoding.NONE,
    )


@mark.order(100)
@mark.cvsa_cloud_master
@mark.cvsa_cloud
@mark.cvsa_aws_master
@mark.cvsa_aws
@mark.cvsa_aws_predefined_application_customer_id
def test_tc01_tc18_tc31_tc32_tc43_tc48(kafka_mgr: KafkaManager, aws: CloudVmManager, billing_kafka: KafkaManager):
    verify_not_deployed_cvsa(cloud_vm_mgr=aws, account_id=kafka_mgr.account_id)
    send_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_backup_requested_event(kafka_mgr, data_protected_gb=1)
    verify_created_event_backup(kafka_mgr, data_protected_gb=1)
    verify_started_event(kafka_mgr)
    cvsa_model = verify_ready_event(kafka_mgr)
    verify_deployed_cvsa(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id)
    verify_vault_credentials(cvsa_id=cvsa_model.cvsa_id)
    verify_instance_type_and_volume_size(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id)
    verify_cloud_stores(cloud_vm_mgr=aws, kafka=kafka_mgr, cloud_bank_name=cvsa_model.catalyst_store)
    verify_storeonce_system(kafka_mgr, aws)
    amount_of_events = verify_billing_event(
        kafka_mgr, billing_kafka, aws, AWS_REGION_1_NAME, cvsa_model.catalyst_store, amount=2
    )
    source_id = write_data_to_cvsa_cloud_store(aws, kafka_mgr, cvsa_model.catalyst_store)
    verify_billing_event(
        kafka_mgr, billing_kafka, aws, AWS_REGION_1_NAME, cvsa_model.catalyst_store, amount=amount_of_events
    )
    validate_cloud_store_data(aws, kafka_mgr)
    # read_data_from_cvsa_cloud_store(aws, kafka_mgr, source_id)
