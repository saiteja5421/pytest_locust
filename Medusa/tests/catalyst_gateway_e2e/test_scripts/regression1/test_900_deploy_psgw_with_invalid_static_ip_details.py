"""
Testrail ID - C57582059 Deploy PSG VM with IP which is already using by another PSG VM

TestRail ID - C57581959 Deploy Protection Store/Protection Store Gateway VM
when static IP details provided to be used for VM creation are incorrect

TestRail ID - C57581960 Deploy Protection Store/Protection Store Gateway VM
when static IP details provided to be used for VM creation are not reachable
"""

import csv
import logging

from pytest import mark, fixture

from lib.common.error_messages import ERROR_MESSAGE_NOT_VALID_NETWORK_DETAILS
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.models.error import Error
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.models.static_ip_details import StaticIPDetails
from requests import codes
from utils.common_helpers import get_project_root as ROOT

from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_psgw_error_messages,
    validate_protection_store_gateway_vm,
    validate_psg_at_error_state_and_task_error_message,
)
from tests.steps.tasks import tasks

logger = logging.getLogger()


def _incorrect_static_ip_details_test_data() -> list[tuple[StaticIPDetails, Error]]:
    """
    Function that parse CSV to list as data provider
    """
    test_data = []
    dir_path = ROOT() / "tests/catalyst_gateway_e2e/test_data/tc_900_invalid_static_ip_details.tsv"
    with open(dir_path) as csv_file:
        for row in csv.DictReader(csv_file, delimiter="\t"):
            error_message = Error(row.pop("error_message"))
            test_data.append((StaticIPDetails(**row), error_message))
    return test_data


@fixture(scope="module")
def context():
    test_context = Context(skip_inventory_exception=True)
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


@mark.order(900)
def test_deploy_psg_with_same_ip(context: Context):
    """
    TestRail ID - C57582059
    Deploy PSG VM with IP which is already using by another PSG VM

    This test is to check whether psg deploy with already using IP. and we Expect DEPLOYED ERROR and in psg should in ERROR state.

    Args:
        context (Context): Context Object
    """
    create_protection_store_gateway_vm(context, add_data_interface=False)
    validate_protection_store_gateway_vm(context)
    context.psgw_name += "_duplicate"
    fail_task_id = create_protection_store_gateway_vm(
        context, add_data_interface=False, expected_status="failed", check_unused_ip=False
    )
    validate_psg_at_error_state_and_task_error_message(context, fail_task_id)


@mark.parametrize("static_ip_details,error", _incorrect_static_ip_details_test_data())
@mark.order(905)
def test_deploy_psgw_with_incorrect_static_ip_details(
    static_ip_details: StaticIPDetails,
    error: Error,
    context: Context,
    shutdown_all_psgw,
):
    """
    TestRail ID - C57581959:
    Deploy Protection Store/Protection Store Gateway VM when static IP details provided to be used for VM creation are incorrect

    Args:
        static_ip_details (StaticIPDetails): Incorrect Static Ip details fetching from tc_900_invalid_static_ip_details.tsv file in test_data
        error (Error): Error message fetching from tc_900_invalid_static_ip_details.tsv file in test_data
        context (Context): Context object
        shutdown_all_psgw (shutdown_all_psgw): Shutdown all created PSGVMs from vCenter
    """
    context.network = static_ip_details.network_ip
    context.netmask = static_ip_details.network_mask
    context.gateway = static_ip_details.network_gateway

    response = create_protection_store_gateway_vm(context=context, return_response=True, check_unused_ip=False)
    validate_psgw_error_messages(response, expected_status_code=codes.bad_request, expected_error=error.message)
