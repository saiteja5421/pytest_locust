"""
    C57582295  - Issue creating protection policy in Backup and Recovery(Unable to see the Created PSG for assigning to policy)-(ESC-10427)
    This was seen in customer place with id:
      ESC-10427 - Issue in creating protection policy in Backup and Recovery(Unable to see the Created PSG for assigning to policy)
      Since the proxy settings was not update during PSG deployment, it was unable to  create cloud store due to proxy configuration issues

    TestRail ID - C57582346
    Validate the deletion of expired cloud backup(AT-21809)

    TestRail ID - C57582096
    Modify network interfaces with duplicate IP's for Protection Store Gateway

    TestRail ID - C57582307
    Validate error message by deploying psg with insufficient storage (ESC-10709)
"""

import logging
from pytest import fixture, mark
from tests.catalyst_gateway_e2e.test_context import Context
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs

from tests.steps.vm_protection.protection_template_steps import (
    assign_protection_template_to_vm,
    create_protection_template,
)
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    perform_do_psg_proxy_check,
    select_or_create_protection_store_gateway_vm,
    add_additional_network_interface_catalyst_gateway_vm,
    validate_error_message_after_modifying_network_interface_with_duplicate_ips,
)
from lib.common.enums.network_interface_type import NetworkInterfaceType
from tests.steps.vm_protection.backup_steps import (
    run_backup,
    change_backup_expiration_time,
    validate_expired_backup_delete,
)
from tests.steps.vm_protection.vmware_steps import VMwareSteps
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.api.catalyst_gateway import CatalystGateway
from tests.steps.vm_protection.common_steps import (
    perform_cleanup,
)
from time import sleep
from lib.common.enums.backup_type_param import BackupTypeParam
from requests import codes
import re
from lib.common.error_messages import (
    ERROR_MESSAGE_ISUFFICIENT_DATASTORE_SPACE,
)

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context()
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(test_context, clean_vm=True)
    logger.info("Teardown Complete".center(20, "*"))


""" 
 TestRail ID C57582295  - 
 Issue creating protection policy in Backup and Recovery(Unable to see the Created PSG for assigning to policy)-(ESC-10427)
"""


@mark.order(3100)
@mark.dependency()
def test_do_psg_proxy_settings_and_check_backups_usage(context, vm_deploy):
    create_protection_store_gateway_vm(context, add_data_interface=False)
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AwsStorageLocation.AWS_EU_NORTH_1)
    perform_do_psg_proxy_check(context)
    assign_protection_template_to_vm(context)
    run_backup(context=context, backup_type=BackupTypeScheduleIDs.cloud)


@mark.order(3110)
@mark.dependency(depends=["test_do_psg_proxy_settings_and_check_backups_usage"])
def test_validate_delete_expired_backup(context):
    """
    TestRail ID - C57582346
    Validate the deletion of expired cloud backup(AT-21809)
    """
    change_backup_expiration_time(BackupTypeParam.backups, context)
    logger.info(f"Waiting for 15 minutes before checking whether expired backup got deleted or not.")
    sleep(900)
    validate_expired_backup_delete(BackupTypeParam.backups, context)


@mark.order(3120)
@mark.dependency()
def test_validate_modify_nic_with_duplicate_IP(context):
    """
    TestRail ID - C57582096
    Modify network interfaces with duplicate IP's for Protection Store Gateway
    """
    select_or_create_protection_store_gateway_vm(context, add_data_interface=False)
    add_additional_network_interface_catalyst_gateway_vm(context, NetworkInterfaceType.data1)
    add_additional_network_interface_catalyst_gateway_vm(context, NetworkInterfaceType.data2)
    validate_error_message_after_modifying_network_interface_with_duplicate_ips(context)


@mark.order(3125)
@mark.dependency()
def test_validate_psg_deployment_with_insufficient_storage(context):
    """
    TestRail ID - C57582307
    Validate error message by deploying psg with insufficient storage (ESC-10709)
    """
    response = create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=10.0,
        max_cld_rtn_days=10,
        max_onprem_dly_prtctd_data=100.0,
        max_onprem_rtn_days=10,
        return_response=True,
    )
    assert response.status_code == codes.bad_request, f"{response.content}"
    response_err_msg = response.json().get("message")
    exp_error_msg = ERROR_MESSAGE_ISUFFICIENT_DATASTORE_SPACE
    assert re.search(
        exp_error_msg, response_err_msg
    ), f"Failed to validate error message EXPECTED: {exp_error_msg} ACTUAL: {response_err_msg}"
    logger.info(f"Successfully validated error message EXPECTED: {exp_error_msg} ACTUAL: {response_err_msg}")
