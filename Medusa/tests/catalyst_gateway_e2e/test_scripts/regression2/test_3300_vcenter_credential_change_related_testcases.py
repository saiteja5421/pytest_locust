"""
    C57582300 - Validate special characters in password during vCenter Registration (ESC-10468)

    C57582294 - Modify the vCenter password and update in DSCC app and continue with backups with updated credentials
"""

import logging
from pytest import fixture, mark
from lib.common.enums.azure_locations import AzureLocations
from tests.catalyst_gateway_e2e.test_context import Context
from tests.steps.vm_protection.common_steps import (
    perform_cleanup,
)
from time import sleep
from tests.steps.vm_protection.vcenter_steps import (
    unregister_vcenter,
    add_vcenter,
    change_vcenter_password,
)
from tests.steps.vm_protection.protection_template_steps import (
    assign_protection_template_to_vm,
    create_protection_template,
)
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
)
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from tests.steps.vm_protection.backup_steps import (
    run_backup,
)
from lib.common.enums.aws_regions import AwsStorageLocation

logger = logging.getLogger()


@fixture(scope="module")
def context():
    context_1 = Context()
    excluded_vcenters = context_1.excluded_vcenters.copy()
    excluded_vcenters.append(context_1.vcenter_name)
    context_2 = Context(excluded_vcenters=excluded_vcenters)
    yield context_2
    logger.info("Teardown Start".center(20, "*"))
    add_vcenter(context_2, extended_timeout=True)
    perform_cleanup(context_2)
    logger.info("Teardown Complete".center(20, "*"))


# Removing this test as we are trying multiple passwords.
# will add the test back ones we add passwords in environment variables of jenkins.
# @mark.order(3300)
# @mark.dependency()
# def test_validate_special_characters_password(context):
#     """
#     C57582300 - Validate special characters in password during vCenter Registration (ESC-10468)
#     """
#     logger.warning(f"Preconditions should be fulfill otherwise test case may get fail.")
#     logger.warning(
#         f"In vcenter {context.vcenter_name} localos user 'test_user' should be added and assigned to Administrator group."
#     )
#     logger.warning(
#         f"On {context.vcenter_name} set 'remember' parameter to 0 in file '/etc/pam.d/system-password' otherwise it may reject the used password for test_user."
#     )
#     original_user = f"{context.vcenter_username}"
#     original_password = f"{context.vcenter_password}"
#     # list of passwords to be validated
#     passwords = []
#     for password in passwords:
#         logger.info(f"Changing password of Vcenter {context.vcenter_name} of user test_user as : '{password}'")
#         change_vcenter_password(context, password)
#         context.vcenter_username = "test_user"
#         context.vcenter_password = f"{password}"
#         # Unregistering vcenter
#         unregister_vcenter(context, force=True)
#         sleep(30)
#         # registering vcenter
#         logger.info(
#             f"Registering {context.vcenter_name} with user as {context.vcenter_username} and password {context.vcenter_password}"
#         )
#         add_vcenter(context, extended_timeout=True)
#         logger.info(
#             f"Successfully added {context.vcenter_name} with {context.vcenter_username}/{context.vcenter_password}"
#         )
#         sleep(30)
#         context.vcenter_username = f"{original_user}"
#         context.vcenter_password = f"{original_password}"


@mark.order(3310)
@mark.dependency(depends=["test_validate_special_characters_password"])
def test_modify_vcenter_password_and_run_backup(context, vm_deploy):
    """
    TestRail ID - C57582294

        Modify the vCenter password and update in DSCC app and continue with backups with updated credentials
    """
    create_protection_store_gateway_vm(context)
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AzureLocations.AZURE_westus3)
    assign_protection_template_to_vm(context)
    run_backup(context, backup_type=BackupTypeScheduleIDs.cloud)
    logger.info(f"Successfully ran backup with updated vcenter credentials.")
    # Unregistering vcenter since vcenter is added in teardown
    unregister_vcenter(context, force=True)
