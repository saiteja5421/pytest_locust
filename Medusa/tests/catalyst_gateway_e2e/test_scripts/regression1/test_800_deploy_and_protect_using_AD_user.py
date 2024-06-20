"""
TestRail ID - C57581952:
    Deploy Protection Store/Protection Store Gateway VM with vcenter AD user
"""

import logging

from pytest import fixture, mark
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.common.enums.azure_locations import AzureLocations
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.backup_steps import run_backup
from tests.steps.vm_protection.protection_template_steps import (
    assign_protection_template_to_vm,
    create_protection_template,
)
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
)
from tests.steps.vm_protection.vcenter_steps import change_vcenter_credentials
from tests.catalyst_gateway_e2e.test_context import Context
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs

logger = logging.getLogger()


# @fixture(scope="module")
# def context():
#     test_context = Context()
#     change_vcenter_credentials(test_context, test_context.ad_username, test_context.ad_password)
#     yield test_context
#     logger.info("Teardown Start".center(20, "*"))
#     change_vcenter_credentials(test_context, test_context.vcenter["username"], test_context.vcenter["password"])
#     perform_cleanup(test_context)
#     logger.info("Teardown Complete".center(20, "*"))


# This test is commented due to there no nimble storage domain added to vcenter.

# @mark.order(800)
# @mark.deploy
# def test_deploy_psgw_using_ad_user(context, vm_deploy, shutdown_all_psgw):
#     """
#     TestRail ID - C57581952:
#         Deploy Protection Store/Protection Store Gateway VM with vcenter AD user
#     """
#     create_protection_store_gateway_vm(
#         context,
#         max_cld_dly_prtctd_data=2.0,
#         max_cld_rtn_days=199,
#         max_onprem_dly_prtctd_data=5.0,
#         max_onprem_rtn_days=99,
#     )
#     validate_protection_store_gateway_vm(context)
#     create_protection_template(context, cloud_region=AzureLocations.AZURE_centralus)
#     assign_protection_template_to_vm(context)
#     run_backup(context, backup_type=BackupTypeScheduleIDs.local)
