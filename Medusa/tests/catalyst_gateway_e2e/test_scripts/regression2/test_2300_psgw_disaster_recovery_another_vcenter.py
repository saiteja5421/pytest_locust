"""
    TestRail ID - C57582139
    Recover a PSG into another vCenter

    TestRail ID - C57582157
    Recover a powered OFF PSG
"""

import logging
import time
from pytest import fixture, mark
from lib.common.enums.azure_locations import AzureLocations
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.vm_protection.protection_template_steps import (
    assign_protection_template_to_vm,
    create_protection_template,
)
from lib.common.enums.psg import HealthState, HealthStatus, State
from tests.steps.vm_protection.backup_steps import (
    run_backup,
)
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    delete_protection_store_gateway_vm_from_vcenter,
    recover_protection_store_gateway_vm,
    wait_for_psg,
    wait_to_get_psgw_to_powered_off,
)
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.api.catalyst_gateway import CatalystGateway
from tests.steps.vm_protection.common_steps import perform_cleanup

logger = logging.getLogger()


@fixture(scope="module")
def context():
    context_1 = Context()
    excluded_vcenters = context_1.excluded_vcenters.copy()
    excluded_vcenters.append(context_1.vcenter_name)
    context_2 = Context(excluded_vcenters=excluded_vcenters)
    yield context_1, context_2
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(context_1)
    perform_cleanup(context_2)
    logger.info("Teardown Complete".center(20, "*"))


"""
    TestRail ID - C57582139
    Recover a PSG into another vCenter
"""
logger.warning("This Test requires two vcenters in ok state,otherwise the test expected to fail")


@mark.order(2300)
@mark.dependency()
def test_recover_psgw_to_another_vcenter(context, vm_deploy):
    vcenter_1, vcenter_2 = context
    # Create psgw with sizer
    create_protection_store_gateway_vm(
        vcenter_1,
    )
    validate_protection_store_gateway_vm(vcenter_1)
    create_protection_template(vcenter_1, cloud_region=AzureLocations.AZURE_swedencentral)
    assign_protection_template_to_vm(vcenter_1)
    run_backup(vcenter_1)

    # Delete PSG VM from vCenter to simulate PSG disaster
    delete_protection_store_gateway_vm_from_vcenter(vcenter_1, force=True)

    # Wait for PSG state become Unknown and health state/status become Unknown/Disconnected
    wait_for_psg(
        vcenter_1, state=State.UNKNOWN, health_state=HealthState.UNKNOWN, health_status=HealthStatus.DISCONNECTED
    )

    # As per the design, PSG Cloud stores needs 15 minutes of idle time before we attempt to "/recover"
    logger.info("PSG Cloud store needs 15min of idle time before attempting '/recover' operation. Sleeping 15mins")
    time.sleep(15 * 60)

    # assigning same psgw name to vcenter_2 context to find the psgw
    vcenter_2.psgw_name = vcenter_1.psgw_name
    # Recovering the psgw into vcenter 2 with psgw id(because the psgw id will same after recovery)
    recover_protection_store_gateway_vm(
        vcenter_2,
        recover_psgw_name=vcenter_2.psgw_name,
    )
    logger.info(f"psgw successfully recovered from vcenter {vcenter_1.vcenter_name} to {vcenter_2.vcenter_name}")
    validate_protection_store_gateway_vm(vcenter_2)


"""
    TestRail ID - C57582157
    Recover a powered OFF PSG
"""


@mark.order(2305)
@mark.recover
@mark.dependency()
def test_recover_powered_off_psg(context, vm_deploy):
    vcenter_1, vcenter_2 = context
    create_protection_store_gateway_vm(
        vcenter_1,
    )
    validate_protection_store_gateway_vm(vcenter_1)
    create_protection_template(vcenter_1, cloud_region=AwsStorageLocation.AWS_US_WEST_2)
    assign_protection_template_to_vm(vcenter_1)
    run_backup(vcenter_1)

    # power off PSG VM from DSCC to simulate PSG disaster
    wait_to_get_psgw_to_powered_off(vcenter_1)

    logger.info("Checking the PSG is changed to powered_off and disconnected state")
    wait_for_psg(vcenter_1, state=State.OK_OFF, health_state=HealthState.OFF, health_status=HealthStatus.DISCONNECTED)

    # As per the design, PSG Cloud stores needs 15 minutes of idle time before we attempt to "/recover"
    logger.info("PSG Cloud store needs 15min of idle time before attempting '/recover' operation. Sleeping 15mins")
    time.sleep(15 * 60)

    # Recover PSG VM
    recover_psgw_name = f"recover_{vcenter_1.psgw_name}"
    recover_protection_store_gateway_vm(
        vcenter_1,
        recover_psgw_name=recover_psgw_name,
    )

    # Perform asset backup should work well with existing local/cloud stores and also the protection policy
    validate_protection_store_gateway_vm(vcenter_1)
    run_backup(vcenter_1)
