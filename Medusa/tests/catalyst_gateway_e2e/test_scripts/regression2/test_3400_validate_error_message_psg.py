"""
    TestRail ID - C57582066
    validate error message while take snapshot of PSG and vm on same datastore
"""

import logging
import json
from pytest import fixture, mark
from lib.common.enums.azure_locations import AzureLocations
from lib.platform.vmware.vcenter_details import get_vm_details_in_a_vcenter
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.vm_protection.protection_template_steps import (
    assign_protection_template_to_vm,
    create_protection_template,
)
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    delete_protection_store_gateway_vm,
)
from lib.common.enums.aws_regions import AwsStorageLocation
from tests.steps.vm_protection.common_steps import perform_cleanup

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context()
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


"""
    TestRail ID - C57582066
    validate error message while take snapshot of PSG and vm on same datastore
"""


@mark.order(3400)
def test_run_snapshot_while_vm_and_psg_on_same_ds(context, vm_deploy):
    logger.warning(
        "This test case requires PSG and VM for backup should be on same datastore, otherwise it is expected to fail"
    )
    # get tiny vm details
    vm_details = get_vm_details_in_a_vcenter(
        context.vm_name, context.vcenter_name, context.vcenter_username, context.vcenter_password
    )
    vm_details_json = json.loads(vm_details)
    vm_datastore = vm_details_json["datastore"][0]
    # setting same datastore for PSG as same as tiny_vm
    psg_datastore_id = context.hypervisor_manager.get_datastore_id(vm_datastore, context.vcenter_name)
    psg_datastore_info = [psg_datastore_id]
    # create psg with same datastore.
    create_protection_store_gateway_vm(context, add_data_interface=False, datastore_info=psg_datastore_info)
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AzureLocations.AZURE_westus3)
    assign_protection_template_to_vm(context, check_error=True)
    # as part of cleanup deleting psg with this datastore, so that it won't affect other testcases.
    delete_protection_store_gateway_vm(context)
