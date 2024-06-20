"""
TC05: Backup/restore request when cVSA Instance need resize. Calculating EBS Volume Size.
    1. Verify that EBS size and cloudbank.
    2. Send cVSARequestedEvent (from Backup Service, or e2e Test suite QA)
    2. Check cVSAStoppedEvent
    3. Check cVSAStartedEvent  (to ensure that instance is running, happens always)
    5. Check cVSAResizedEvent
    6. Check cVSAReadyEvent
    7. Verify that EBS size was changed
"""

import logging
from dataclasses import dataclass
from typing import List

from pytest import mark

from lib.common.enums.cloud_instance_details import CloudInstanceDetails
from lib.common.enums.cvsa import RequestFinishedStatus, CloudProvider
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from tests.steps.aws_protection.cvsa.backup_request_steps import (
    send_backup_requested_event,
    verify_backup_requested_event,
)
from tests.steps.aws_protection.cvsa.cloud_steps import verify_deployed_cvsa
from tests.steps.aws_protection.cvsa.cvsa_manager_steps import (
    verify_resize_event,
    verify_ready_event,
    verify_instance_type_and_volume_size,
    send_finished_event,
    verify_finished_event,
    create_new_cvsa_instance_and_validate,
)
from tests.steps.aws_protection.cvsa.storeonce_steps import verify_storeonce_system


@dataclass
class ResizeParam:
    protected_data_gb: int
    prev_protected_data_gb: int
    backup_streams: int or None
    volume_size_bytes: int
    instance_details: CloudInstanceDetails
    resize_allowed: bool = True


@mark.order(510)
@mark.cvsa_cloud
@mark.cvsa_azure
@mark.parametrize(
    "cloud_vm_mgr, parameters",
    [
        # # Azure tests temporary disabled
        # (
        #     "azure",
        #     [
        #         ResizeParam(1, 0, None, 50_465_865_728, CloudInstanceDetails.Standard_E2S_v5),
        #         # calculated for disk usage 212 MB
        #         ResizeParam(8_000, 3_000, 8, 104_830_000_000, CloudInstanceDetails.Standard_D16ls_v5),
        #         ResizeParam(1, 8_000, 8, 104_830_000_000, CloudInstanceDetails.Standard_D4S_v5),
        #     ],
        # ),
        (
            "aws",
            [
                ResizeParam(20_000, 0, 8, 230_000_000_000, CloudInstanceDetails.C6I_8XLARGE),
                ResizeParam(3_000, 20_000, 8, 230_000_000_000, CloudInstanceDetails.C6I_4XLARGE),
                ResizeParam(30_000, 3_000, 11, 346_828_681_728, CloudInstanceDetails.C6I_12XLARGE),
                ResizeParam(50_000, 30_000, 18, 346_828_681_728, CloudInstanceDetails.C6I_24XLARGE, False),
            ],
        ),
    ],
)
def test_tc05(kafka_mgr: KafkaManager, cloud_vm_mgr: CloudVmManager, parameters: List[ResizeParam], request):
    cloud_vm_mgr = request.getfixturevalue(cloud_vm_mgr)

    logging.info("Step 1. Create instance and validate")
    create_new_cvsa_instance_and_validate(
        cloud_vm_mgr=cloud_vm_mgr,
        kafka_mgr=kafka_mgr,
        data_protected_gb=parameters[0].protected_data_gb,
        instance_details=parameters[0].instance_details,
        volume_size_bytes=parameters[0].volume_size_bytes,
        backup_streams=parameters[0].backup_streams,
    )
    send_finished_event(kafka_mgr, cloud_provider=cloud_vm_mgr.name())

    for parameter in parameters[1:]:
        logging.info(f"Verify resizing to: {parameter}")
        verify_instance_scaling(
            kafka_mgr=kafka_mgr,
            cloud_vm_mgr=cloud_vm_mgr,
            backup_streams=parameter.backup_streams,
            volume_size_bytes=parameter.volume_size_bytes,
            protected_data_gb=parameter.protected_data_gb,
            prev_protected_data_gb=parameter.prev_protected_data_gb,
            instance_details=parameter.instance_details,
            resize_allowed=parameter.resize_allowed,
        )


def verify_instance_scaling(
    kafka_mgr,
    cloud_vm_mgr: CloudVmManager,
    backup_streams: int,
    volume_size_bytes: int,
    protected_data_gb: int,
    prev_protected_data_gb: int,
    instance_details: CloudInstanceDetails,
    resize_allowed=True,
):
    cloud_provider = cloud_vm_mgr.name()
    send_backup_requested_event(
        kafka_manager=kafka_mgr,
        data_protected_gb=protected_data_gb,
        data_protected_previous_gb=prev_protected_data_gb,
        cloud_provider=cloud_provider,
    )
    verify_backup_requested_event(
        kafka=kafka_mgr, data_protected_gb=protected_data_gb, cloud_provider=cloud_vm_mgr.name()
    )
    if not resize_allowed:
        verify_finished_event(
            kafka_mgr,
            result=RequestFinishedStatus.STATUS_ERROR,
            error_msg="You've reached the maximum modification rate per volume limit",
            timeout=4000,
            cloud_provider=cloud_vm_mgr.name(),
        )
        return
    verify_resize_event(
        kafka_mgr,
        protected_data_gb,
        instance_details,
        backup_streams,
        volume_size_bytes,
        cloud_provider=cloud_vm_mgr.name(),
    )
    verify_ready_event(
        kafka_mgr,
        instance_details,
        backup_streams,
        volume_size_bytes,
        cloud_provider=cloud_provider,
    )
    verify_deployed_cvsa(cloud_vm_mgr=cloud_vm_mgr, cvsa_id=kafka_mgr.cvsa_id)
    logging.info("Verify that volume size was changed")
    verify_instance_type_and_volume_size(
        cloud_vm_mgr=cloud_vm_mgr,
        cvsa_id=kafka_mgr.cvsa_id,
        instance_details=instance_details,
        volume_size_bytes=volume_size_bytes,
    )

    if cloud_vm_mgr.name() == CloudProvider.AZURE:
        logging.info("Skipping StoreOnce check after resize for Azure instance due to cVSA image issues")
    else:
        verify_storeonce_system(kafka_mgr, cloud_vm_mgr, volume_size_bytes)

    send_finished_event(kafka_mgr, cloud_provider=cloud_provider)
    verify_finished_event(kafka_mgr, cloud_provider=cloud_provider)
