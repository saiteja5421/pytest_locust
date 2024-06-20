"""
TC42: Resize cVSA instance while customer has already one stopped cvsa instance in a different region
    Prerequisites: customer has two idle instances already deployed in two different regions
    1.  Verify that cVSA instances exists and are stopped
    2. Send cVSARequestedEvent for one cvsa instance.
    3. Check cVSAResizeEvent
    4. Check cVSAStartedEvent (at this point cVSA is in running state within AWS and monitoring is triggered)
    5. Check cVSAReadyEvent (At this point cVSA is ready)
    6. Verify that only resized requested cvsa instance is running state
"""

from pytest import fixture, mark

from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.common.enums.cvsa import AwsRegions, StopReason
from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.cloud.cloud_dataclasses import CloudInstanceState
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.functional.aws_protection.cvsa_manager.constants import AWS_REGION_1_NAME
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cloud_steps import verify_instance_state
from tests.steps.aws_protection.cvsa.common_steps import cleanup_cvsa_instances
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    send_finished_event,
    verify_finished_event,
    create_new_cvsa_instance_and_validate,
    verify_stopped_event,
    verify_resize_event,
    verify_ready_event,
    verify_instance_type_and_volume_size,
)
from tests.steps.aws_protection.cvsa.kafka import new_kafka_lifecycle_events


@fixture(scope="function")
def kafka_mgr(aws_west, aws_north):
    kafka_mgr_west = new_kafka_lifecycle_events(tc_id=42)
    kafka_mgr_north = new_kafka_lifecycle_events(
        tc_id=42,
        account_id=kafka_mgr_west.account_id,
    )
    kafka_mgr_north.cam_account_id = kafka_mgr_west.cam_account_id
    kafka_mgr_north.csp_account_id = kafka_mgr_west.csp_account_id
    yield kafka_mgr_west, kafka_mgr_north
    send_finished_event(kafka_mgr_west)
    send_finished_event(kafka_mgr_north)
    cleanup_cvsa_instances(kafka_mgr_west, [aws_west, aws_north])


@fixture(scope="function")
def aws_west():
    return AWS(
        region_name=AWS_REGION_1_NAME,
        aws_access_key_id="test",
        aws_secret_access_key="test",
    ).ec2


@fixture(scope="function")
def aws_north():
    return AWS(
        region_name="eu-north-1",
        aws_access_key_id="test",
        aws_secret_access_key="test",
    ).ec2


@mark.order(3600)
@mark.cvsa_localstack
def test_tc42(kafka_mgr: KafkaManager, aws_west, aws_north):
    region_north = AwsRegions.AWS_EU_NORTH_1
    kafka_mgr_west, kafka_mgr_north = kafka_mgr
    # Create instance on eu-north-1
    north_cvsa_model = create_new_cvsa_instance_and_validate(
        cloud_vm_mgr=aws_north, kafka_mgr=kafka_mgr_north, data_protected_gb=1, cloud_region=region_north
    )
    # Create instance on eu-west-1
    west_cvsa_model = create_new_cvsa_instance_and_validate(
        cloud_vm_mgr=aws_west, kafka_mgr=kafka_mgr_west, data_protected_gb=1
    )
    # Send finished and wait for idle on eu-north-1
    send_finished_event(kafka_mgr_north, cloud_region=region_north)
    verify_finished_event(kafka_mgr_north, cloud_region=region_north)
    verify_stopped_event(kafka_mgr_north, reason=StopReason.IDLE)
    verify_instance_state(aws_north, kafka_mgr_north.account_id, CloudInstanceState.STOPPED, timeout_seconds=5)
    # Send finished event on eu-west-1 to start new backup request
    send_finished_event(kafka_mgr_west)
    verify_finished_event(kafka_mgr_west)
    # Verify that instance on different regions are different
    assert north_cvsa_model.cvsa_id != west_cvsa_model.cvsa_id
    assert north_cvsa_model.cloud_region != west_cvsa_model.cloud_region
    assert north_cvsa_model.catalyst_store != west_cvsa_model.catalyst_store
    # Send new backup request on eu-west-1 with resize required
    send_backup_requested_event(kafka_mgr_west, data_protected_gb=30_000, data_protected_previous_gb=1)
    verify_backup_requested_event(kafka_mgr_west, data_protected_gb=30_000, data_protected_previous_gb=1)
    # Verify resize and ready
    verify_resize_event(
        kafka_mgr_west,
        data_protected_gb=30_000,
        instance_details=CloudInstanceDetails.C6I_12XLARGE,
        backup_streams=10,
        volume_size_bytes=340_000_200_000,
    )
    west_cvsa_model_after_resize = verify_ready_event(
        kafka_mgr_west,
        instance_details=CloudInstanceDetails.C6I_12XLARGE,
        backup_streams=10,
        volume_size_bytes=340_000_200_000,
    )
    # Verify that common fields are the same for new request
    assert west_cvsa_model_after_resize.cvsa_id == west_cvsa_model.cvsa_id
    assert west_cvsa_model_after_resize.cloud_region == west_cvsa_model.cloud_region
    assert west_cvsa_model_after_resize.catalyst_store == west_cvsa_model.catalyst_store
    # Verify EC2 and EBS size for resized instance
    verify_instance_type_and_volume_size(
        cloud_vm_mgr=aws_west,
        cvsa_id=kafka_mgr_west.cvsa_id,
        instance_details=CloudInstanceDetails.C6I_12XLARGE,
        volume_size_bytes=340_000_200_000,
    )
    # Verify that eu-north-1 instance is stopped
    verify_instance_state(aws_north, kafka_mgr_north.account_id, CloudInstanceState.STOPPED, timeout_seconds=5)
    # Verify EC2 Type and EBS size on eu-north-1 instance is not changed
    verify_instance_type_and_volume_size(cloud_vm_mgr=aws_north, cvsa_id=kafka_mgr_north.cvsa_id)
