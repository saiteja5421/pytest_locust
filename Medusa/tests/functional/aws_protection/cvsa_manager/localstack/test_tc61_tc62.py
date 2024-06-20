"""
TC61: First-time backup request with target_duration_seconds parameter filled
    - Resize backup request with target_duration_seconds parameter filled
"""
from dataclasses import dataclass
from typing import Optional

from pytest import mark

from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cloud_steps import verify_deployed_cvsa
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_started_event,
    verify_ready_event,
    create_new_cvsa_instance_and_validate,
    send_finished_event,
    verify_finished_event,
    verify_resize_event,
    verify_instance_type_and_volume_size,
)

_ONE_HOUR = 3600


@dataclass
class Request:
    prev_protected_data_gb: int
    protected_data_gb: int
    instance_details: CloudInstanceDetails
    backup_streams: int
    target_duration_seconds: Optional[int]
    ebs_size: int


@mark.cvsa_localstack
@mark.cvsa_localstack_pr
@mark.parametrize(
    "first_request, resize_request",
    [
        # 1st case - normal request to resize requests with target_duration_seconds
        (
            Request(0, 1, CloudInstanceDetails.R6I_LARGE, 8, None, 50000000000),
            Request(1, 4000, CloudInstanceDetails.C6I_12XLARGE, 10, 1 * _ONE_HOUR, 54002000000),
        ),
        # 2nd case - request with target_duration_seconds to normal resize request
        (
            Request(0, 2000, CloudInstanceDetails.C6I_4XLARGE, 8, 2 * _ONE_HOUR, 50000000000),
            Request(2000, 1, CloudInstanceDetails.R6I_LARGE, 8, None, 50000000000),
        ),
        # 3rd case - requests with target_duration_seconds to resize requests with target_duration_seconds
        (
            Request(0, 5000, CloudInstanceDetails.C6I_4XLARGE, 8, 5 * _ONE_HOUR, 65000000000),
            Request(5000, 10000, CloudInstanceDetails.C6I_8XLARGE, 8, 4 * _ONE_HOUR, 131000000000),
        ),
    ],
)
def test_tc61(kafka_mgr: KafkaManager, aws: CloudVmManager, first_request, resize_request):
    create_new_cvsa_instance_and_validate(
        cloud_vm_mgr=aws,
        kafka_mgr=kafka_mgr,
        data_protected_gb=first_request.protected_data_gb,
        backup_streams=first_request.backup_streams,
        instance_details=first_request.instance_details,
        volume_size_bytes=first_request.ebs_size,
        target_duration_seconds=first_request.target_duration_seconds,
        strict_instance_details=True,
    )
    send_finished_event(kafka_mgr)
    verify_finished_event(kafka_mgr)
    send_backup_requested_event(
        kafka_mgr,
        data_protected_gb=resize_request.protected_data_gb,
        data_protected_previous_gb=resize_request.prev_protected_data_gb,
        target_duration_seconds=resize_request.target_duration_seconds,
    )
    verify_backup_requested_event(
        kafka_mgr,
        data_protected_gb=resize_request.protected_data_gb,
        data_protected_previous_gb=resize_request.prev_protected_data_gb,
        target_duration_seconds=resize_request.target_duration_seconds,
    )
    verify_started_event(kafka_mgr)
    verify_resize_event(
        kafka_mgr,
        data_protected_gb=resize_request.protected_data_gb,
        backup_streams=resize_request.backup_streams,
        instance_details=resize_request.instance_details,
        volume_size_bytes=resize_request.ebs_size,
        strict_instance_details=True,
    )
    verify_ready_event(
        kafka_mgr,
        instance_details=resize_request.instance_details,
        backup_streams=resize_request.backup_streams,
        volume_size_bytes=resize_request.ebs_size,
        strict_instance_details=True,
    )
    verify_deployed_cvsa(cloud_vm_mgr=aws, cvsa_id=kafka_mgr.cvsa_id)
    verify_instance_type_and_volume_size(
        cloud_vm_mgr=aws,
        cvsa_id=kafka_mgr.cvsa_id,
        instance_details=resize_request.instance_details,
        volume_size_bytes=resize_request.ebs_size,
        strict_instance_details=True,
    )
