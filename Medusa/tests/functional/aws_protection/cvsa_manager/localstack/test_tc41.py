"""
TC41: Deploy a new cVSA instance while customer has already one idle cvsa instance in a different region
    1. Verify that cVSA instance exists and is stopped
    2. Send cVSARequestedEvent for different region.
    3. Check cVSACreatedEvent
    4. Check cVSAStartedEvent (at this point cVSA is in running state within AWS and monitoring is triggered)
    5. Check cVSAReadyEvent (At this point cVSA is ready)
    6. Verify that only new requested cvsa instance is running state
"""

from pytest import fixture, mark

from lib.common.enums.cvsa import AwsRegions, StopReason
from lib.common.enums.ec2_state import Ec2State
from lib.platform.aws_boto3.aws_factory import AWS
from lib.platform.cloud.cloud_dataclasses import CloudInstanceState
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.functional.aws_protection.cvsa_manager.constants import AWS_REGION_1_NAME
from tests.steps.aws_protection.cvsa.cloud_steps import verify_instance_state
from tests.steps.aws_protection.cvsa.common_steps import cleanup_cvsa_instances
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    send_finished_event,
    verify_finished_event,
    create_new_cvsa_instance_and_validate,
    verify_stopped_event,
)
from tests.steps.aws_protection.cvsa.kafka import new_kafka_lifecycle_events


@fixture(scope="function")
def kafka_mgr(aws_west, aws_north):
    kafka_mgr = new_kafka_lifecycle_events(tc_id=41)
    yield kafka_mgr
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)
    cleanup_cvsa_instances(kafka_mgr, [aws_west, aws_north])


@fixture(scope="function")
def aws_west():
    return AWS(region_name=AWS_REGION_1_NAME, aws_access_key_id="test", aws_secret_access_key="test").ec2


@fixture(scope="function")
def aws_north():
    return AWS(region_name="eu-north-1", aws_access_key_id="test", aws_secret_access_key="test").ec2


@mark.cvsa_localstack
def test_tc41(kafka_mgr: KafkaManager, aws_north, aws_west):
    create_new_cvsa_instance_and_validate(
        cloud_vm_mgr=aws_north,
        kafka_mgr=kafka_mgr,
        data_protected_gb=1,
        cloud_region=AwsRegions.AWS_EU_NORTH_1,
    )
    send_finished_event(kafka_mgr, cloud_region=AwsRegions.AWS_EU_NORTH_1)
    verify_finished_event(kafka_mgr, cloud_region=AwsRegions.AWS_EU_NORTH_1)
    verify_stopped_event(kafka_mgr, reason=StopReason.IDLE)
    verify_instance_state(aws_north, kafka_mgr.account_id, CloudInstanceState.STOPPED, timeout_seconds=1500)

    create_new_cvsa_instance_and_validate(
        cloud_vm_mgr=aws_west,
        kafka_mgr=kafka_mgr,
        data_protected_gb=1,
    )
    verify_instance_state(aws_north, kafka_mgr.account_id, CloudInstanceState.STOPPED, timeout_seconds=30)
    verify_instance_state(aws_west, kafka_mgr.account_id, CloudInstanceState.RUNNING, timeout_seconds=30)
