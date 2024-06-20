"""
TC05: TC is made for local run purposes only. Backup/restore request when cVSA Instance need resize.
    Checking resize for all available compute types starting from Standard_E2S.
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


@mark.parametrize(
    "cloud_vm_mgr, parameters",
    [
        (
            "azure",
            [
                ResizeParam(1, 0, None, 50_465_865_728, CloudInstanceDetails.Standard_E2S_v5),
                ResizeParam(2_000, 1, 8, 50_465_865_728, CloudInstanceDetails.Standard_D4S_v5),
                ResizeParam(4_000, 2_000, 8, 58_635_865_728, CloudInstanceDetails.Standard_D8s_v5),
                ResizeParam(8_000, 4_000, 8, 107_030_000_000, CloudInstanceDetails.Standard_D16S_v5),
                ResizeParam(12_000, 8_000, 8, 159_830_000_000, CloudInstanceDetails.Standard_E20s_v5),
                ResizeParam(14_000, 12_000, 9, 190_630_000_000, CloudInstanceDetails.Standard_D32s_v5),
                ResizeParam(25_000, 14_000, 9, 316_030_000_000, CloudInstanceDetails.Standard_D48s_v5),
                ResizeParam(35_000, 25_000, 9, 450_230_000_000, CloudInstanceDetails.Standard_D64s_v5),
                ResizeParam(45_000, 35_000, 8, 582_230_000_000, CloudInstanceDetails.Standard_D96s_v5),
            ],
        ),
    ],
)
def test_tc05_manual(kafka_mgr: KafkaManager, cloud_vm_mgr: CloudVmManager, parameters: List[ResizeParam], request):
    cloud_vm_mgr = request.getfixturevalue(cloud_vm_mgr)

    logging.info("Create instance and validate")
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
        )


def verify_instance_scaling(
    kafka_mgr,
    cloud_vm_mgr: CloudVmManager,
    backup_streams: int,
    volume_size_bytes: int,
    protected_data_gb: int,
    prev_protected_data_gb: int,
    instance_details: CloudInstanceDetails,
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
    verify_storeonce_system(kafka_mgr, cloud_vm_mgr, volume_size_bytes)
    send_finished_event(kafka_mgr, cloud_provider=cloud_provider)
    verify_finished_event(kafka_mgr, cloud_provider=cloud_provider)
