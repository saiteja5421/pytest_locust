import logging
from pytest import fixture, mark
from lib.common.enums.restore_type import RestoreType
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.protection_template_steps import (
    assign_protection_template_to_vm,
    create_protection_template,
    unassign_protecion_policy_from_vm,
    delete_unassinged_protection_policy,
)
from tests.steps.vm_protection.backup_steps import (
    restore_virtual_machine,
    run_backup,
)
from lib.common.enums.aws_regions import AwsStorageLocation
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    select_or_create_protection_store_gateway_vm,
    validate_error_msg_exprireafter_value_100_year_with_lockforvalue_100_years,
    validate_error_msg_retention_period_is_5_years_with_lock_for_option_with_100_years,
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


"""
The below test order  2000 & 2005 commented due to the protection policy is created
with lockfor parameter and lock the backup.
it is not possible to delete backup vm and it become a stale vm 
"""
# @mark.order(2000)
# @mark.dependency()
# def test_retention_period_is_5_years_with_lock_for_option_with_100_years(context):
#     """
#     Testrail id:C57598484
#     Retention period is 5 years with lock for option 100 years
#     """
#     create_protection_store_gateway_vm(context)
#     validate_error_msg_retention_period_is_5_years_with_lock_for_option_with_100_years(
#         context,
#         cloud_region=AwsStorageLocation.AWS_US_WEST_2,
#         onprem_expire_value=5,
#         cloud_expire_value=5,
#         onprem_lockfor_value=100,
#         cloud_lockfor_value=100,
#     )


# @mark.order(2005)
# @mark.dependency(depends=["test_retention_period_is_5_years_with_lock_for_option_with_100_years"])
# @mark.deploy
# def test_retention_period_with_lockfor_option_with_100_years(context, vm_deploy):
#     """
#     Testrail id:C57598483
#     Retention period 100 years with lockfor option 100 years
#     """
#     select_or_create_protection_store_gateway_vm(context)
#     create_protection_template(
#         context,
#         cloud_region=AwsStorageLocation.AWS_EU_WEST_2,
#         onprem_expire_value=100,
#         cloud_expire_value=100,
#         onprem_lockfor_value=100,
#         cloud_lockfor_value=100,
#     )
#     validate_error_msg_exprireafter_value_100_year_with_lockforvalue_100_years(context)
#     unassign_protecion_policy_from_vm(context)
#     delete_unassinged_protection_policy(context)


@mark.order(2010)
@mark.dependency()
@mark.deploy
def test_retention_period_without_lockfor_option(context, vm_deploy):
    """
    Testrail id:C57598485
    Retention period without lockfor option
    """
    select_or_create_protection_store_gateway_vm(context)
    create_protection_template(
        context,
        cloud_region=AwsStorageLocation.AWS_EU_WEST_2,
        onprem_expire_value=100,
        cloud_expire_value=100,
    )
    assign_protection_template_to_vm(context)
    run_backup(context)
    restore_virtual_machine(context, RestoreType.new, "cloud")
    restore_virtual_machine(context, RestoreType.existing, "cloud", quite_time=120)
