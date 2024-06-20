"""
    TestRail ID - C57582347
    PSG Powered OFF and cloud store creation is still with 'Creating' state (AT-17320)
"""

import time
import logging
from pytest import fixture, mark
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.common.enums.azure_locations import AzureLocations
from lib.common.enums.psg import HealthState, HealthStatus, State
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.protection_template_steps import (
    create_protection_template,
    assign_protection_template_to_vm,
)
from tests.steps.vm_protection.backup_steps import (
    run_backup,
)
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    create_cloud_protection_during_recover_protection_store_gateway_vm,
    create_cloud_protection_store_before_recover_and_validate_its_creation_after_recover,
    delete_protection_store_gateway_vm_from_vcenter,
    wait_for_psg,
    select_or_create_protection_store_gateway_vm,
    wait_to_get_psgw_to_powered_off,
    create_and_validate_cloud_store_when_psg_poweredoff,
)
from tests.catalyst_gateway_e2e.test_context import Context

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context()
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


@mark.order(3200)
@mark.dependency()
def test_check_cloud_protection_store_created_during_recover(context, vm_deploy):
    create_protection_store_gateway_vm(
        context,
        add_data_interface=False,
    )
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AwsStorageLocation.AWS_EU_NORTH_1)
    assign_protection_template_to_vm(context)
    run_backup(context)

    # Delete PSG VM from vCenter to simulate PSG disaster
    delete_protection_store_gateway_vm_from_vcenter(context, force=True)

    # Wait for PSG state become Unknown and health state/status become Unknown/Disconnecte
    wait_for_psg(
        context, state=State.UNKNOWN, health_state=HealthState.UNKNOWN, health_status=HealthStatus.DISCONNECTED
    )

    # As per the design, PSG Cloud stores needs 15 minutes of idle time before we attempt to "/recover"
    logger.info("PSG Cloud store needs 15min of idle time before attempting '/recover' operation. Sleeping 15mins")
    time.sleep(15 * 60)
    recover_psgw_name = f"recover_{context.psgw_name}"
    create_cloud_protection_during_recover_protection_store_gateway_vm(
        context,
        recover_psgw_name=recover_psgw_name,
        add_data_interface=False,
    )
    validate_protection_store_gateway_vm(context)


@mark.order(3205)
@mark.dependency()
def test_create_cloud_store_when_psg_is_power_off(context):
    """
    TestRail ID - C57582347
    PSG Powered OFF and cloud store creation is still with 'Creating' state (AT-17320)
    """
    select_or_create_protection_store_gateway_vm(context)

    create_protection_template(context, cloud_region=AwsStorageLocation.AWS_US_WEST_2)
    assign_protection_template_to_vm(context)

    logger.info(f"PSG powering off:")
    wait_to_get_psgw_to_powered_off(context)

    # Creating cloud protection store with new region
    create_and_validate_cloud_store_when_psg_poweredoff(context, cloud_region=AzureLocations.AZURE_westeurope)


@mark.order(3210)
@mark.dependency()
def test_check_cloud_protection_store_created_before_recover(context, vm_deploy):
    create_protection_store_gateway_vm(
        context,
        add_data_interface=False,
    )
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AzureLocations.AZURE_westus2)
    assign_protection_template_to_vm(context)
    run_backup(context)

    # Delete PSG VM from vCenter to simulate PSG disaster
    delete_protection_store_gateway_vm_from_vcenter(context, force=True)

    # Wait for PSG state become Unknown and health state/status become Unknown/Disconnecte
    wait_for_psg(
        context, state=State.UNKNOWN, health_state=HealthState.UNKNOWN, health_status=HealthStatus.DISCONNECTED
    )
    logger.info("PSG Cloud store needs 15min of idle time before attempting '/recover' operation. Sleeping 15mins")
    time.sleep(15 * 60)
    create_cloud_protection_store_before_recover_and_validate_its_creation_after_recover(context)
    logger.info("Successfully verified cloud protection store is created")
