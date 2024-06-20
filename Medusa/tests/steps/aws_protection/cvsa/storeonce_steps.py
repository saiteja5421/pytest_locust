import logging

import assertpy
from pytest_check import check
from waiting import TimeoutExpired, wait

from lib.common.enums.cvsa import VaultCredentialType, CloudProvider
from lib.platform.cloud.cloud_vm_manager import CloudVmManager
from lib.platform.kafka.kafka_manager import KafkaManager
from lib.platform.storeonce.storeonce import StoreOnce
from tests.steps.aws_protection.cvsa.cloud_steps import (
    get_storeonce_ip,
    get_cvsa_version,
    get_cvsa_private_ip,
)
from tests.steps.aws_protection.cvsa.vault_steps import get_cvsa_credentials

logger = logging.getLogger()


def get_cvsa_storeonce(cloud_vm_mgr: CloudVmManager, kafka: KafkaManager) -> StoreOnce:
    storeonce_ip = get_storeonce_ip(cloud_vm_mgr=cloud_vm_mgr, cvsa_id=kafka.cvsa_id)
    credential = get_cvsa_credentials(kafka.cvsa_id, VaultCredentialType.ADMIN)
    storeonce = StoreOnce(host=storeonce_ip, username=credential.username, password=credential.password)
    return storeonce


def validate_cloud_store_data(cloud_vm_mgr: CloudVmManager, kafka: KafkaManager):
    logger.info(f"Validate uploaded data to cloud store: {kafka.account_id}")
    storeonce = get_cvsa_storeonce(cloud_vm_mgr, kafka)

    def _wait_for_job_status_completed():
        try:
            cloud_store = storeonce.get_cloud_store()
            if (
                cloud_store.user_bytes > 0
                and cloud_store.dedupe_ratio > 0.0
                and cloud_store.num_items > 0
                and cloud_store.cloud_store_details.cloud_disk_bytes > 2496
            ):
                return True
        except KeyError as e:
            logger.warn(f"Data extractor volume copy job waits: {e}")

    try:
        wait(_wait_for_job_status_completed, timeout_seconds=900, sleep_seconds=15)
    except TimeoutExpired as e:
        logger.info("Data extractor volume copy job failed.")
        raise e
    logger.info(f"Success - Validate uploaded data to cloud store: {kafka.account_id}")


def verify_storeonce_system(
    kafka: KafkaManager, cloud_vm_mgr: CloudVmManager, volume_size_bytes=50_000_000_000, user_bytes_expected=0
):
    logger.info(f"Verify storeonce health and ebs size:{volume_size_bytes}")
    storeonce = get_cvsa_storeonce(cloud_vm_mgr, kafka)
    storeonce.verify_health_cvsa()
    storeonce.verify_stores(local_capacity_bytes=volume_size_bytes, user_bytes_expected=user_bytes_expected)

    ntp_servers = storeonce.get_ntp_servers()
    logger.info(f"Verifying NTP Server Settings: {ntp_servers}")
    with check:
        # TODO: Check NTP server state for all Cloud Providers.
        if cloud_vm_mgr.name() == CloudProvider.AWS:
            assert ntp_servers.enabled is True
            assert ntp_servers.health_state.state == "OK"
            assert len(ntp_servers.ntp_server_name) == 1
            assert ntp_servers.ntp_server_name[0] == cloud_vm_mgr.get_ntp_server_address()
            logger.info("NTP Server Settings verified")

        system_information = storeonce.get_system_information()
        logger.info(f"Verifying System Information: {system_information}")
        assertpy.assert_that(storeonce.get_temp_support_password_mode()).is_equal_to("TIMEBASED")
        # Below statement is required due to Catalyst API that does not accept UUID for Application Customer ID
        assert system_information.application_customer_id == "".join(kafka.account_id.decode("UTF-8").split("-"))
        assert system_information.cat_gateway_id
        assert not system_information.contact_email
        assert system_information.contact_name == "Internal User"
        assert system_information.hostname
        assert system_information.management_address == get_cvsa_private_ip(kafka, cloud_vm_mgr)
        assert not system_information.ope_token
        assert system_information.operational_mode == "PRODUCTION"
        assert system_information.platform_customer_id
        assert system_information.product_name == "HPE Catalyst Gateway VSA"
        assert system_information.product_sku
        assert system_information.serial_number
        assert system_information.software_version == get_cvsa_version(cloud_vm_mgr, kafka.cvsa_id)
        assert not system_information.system_location
        assert system_information.system_uuid
        assert system_information.warranty_serial_number
        logger.info("System Information verified")


def verify_cloud_stores(kafka: KafkaManager, cloud_vm_mgr: CloudVmManager, cloud_bank_name: str):
    logger.info(f"Verify Cloud Stores for cVSA: {cloud_bank_name}, customer: {kafka.account_id}")
    storeonce = get_cvsa_storeonce(cloud_vm_mgr, kafka)
    cloud_stores = storeonce.get_cloud_stores()
    assert len(cloud_stores) == 1
    assert cloud_stores[0].name == cloud_bank_name
    store_permissions = storeonce.get_store_permissions()
    assert store_permissions[1].name == "store"
    assert store_permissions[1].allow_access is True
    logger.info(f"Cloud Stores verified for cVSA: {cloud_bank_name}, customer: {kafka.account_id}")


def verify_support_bundle(kafka: KafkaManager, cloud_vm_mgr: CloudVmManager, bundle_count=1):
    logger.info(f"Verify support bundle count: {bundle_count}")
    storeonce = get_cvsa_storeonce(cloud_vm_mgr, kafka)
    logs = storeonce.get_support_bundle_logs("daily")
    assert bundle_count == len(logs)
    logger.info(f"Support bundle count: {bundle_count} verified")
