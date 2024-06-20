"""
TestRail ID: C57581936
    Deploy protection store gateway VM on a registered vcenter where OPE is not deployed.

TestRail ID: C57581954
    Deploy protection store gateway VM with max local store supported capacity

TestRail ID - C57582216
    Validate the create PSGW, datastore wizard

TestRail ID: C57581955
    List and validate local store/s after successful creation

TestRail ID: C57581956
    Validate various deployment states such as initializing, deploying, registering, and ok while protection store gateway vm is in progress

TestRail ID: C57582224
    Validate PSGW deployment with morethan supported capacity using sizer params

"""

import logging

from pytest import fixture, mark
from requests import codes

from lib.common.enums.aws_regions import AwsStorageLocation
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    validate_psgw_error_messages,
)
from tests.steps.vm_protection.protection_template_steps import (
    create_protection_template,
    assign_protection_template_to_vm,
)
from tests.steps.vm_protection.backup_steps import run_backup
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from tests.catalyst_gateway_e2e.test_context import Context
from lib.common.error_messages import ERROR_MESSAGE_ONPREM_DAILY_PROTECTED_DATA

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context(v_center_type="VCENTER1")
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


@mark.order(200)
@mark.deploy
def test_deploy_psgw_with_max_capacity_on_non_ope_vcenter(context, vm_deploy):
    """TestRail ID: C57581936
        Deploy protection store gateway VM on a registered vcenter where OPE is not deployed.

    TestRail ID: C57581954
        Deploy protection store gateway VM with max local store supported capacity

    TestRail ID - C57582216
        Validate the create PSGW, datastore wizard

    TestRail ID: C57581955
        List and validate local store/s after successful creation

    TestRail ID: C57581956
        Validate various deployment states such as initializing, deploying, registering, and ok while protection store gateway vm is in progress
    """
    non_do_hosted_vc = context.test_data["non_do_hosted_vc"]
    logger.warning(
        f"Data Orchestrator 'DO' should not be deployed on the vCenter: {non_do_hosted_vc}, otherwise intention of this test will be deviated..."
    )
    assert (
        context.vcenter_name == non_do_hosted_vc
    ), f"Failed to deploy the PSGW, VC: {context.vcenter_name} and non do hosted vc: {non_do_hosted_vc} doesn't matached"
    logger.info(f"Running the test against to the VC: {context.vcenter_name} and non do hosted vc: {non_do_hosted_vc}")
    vc_name = context.vcenter_name.split(".")
    array_name = context.array.split(".")
    additional_ds_name = f"{vc_name[0]}-{array_name[0]}-PSG-DS"
    logger.warning(
        f"We need to create datastores to accomodate psgw capacity and datastore name must contains: {additional_ds_name} on vCenter: {context.vcenter_name} otherwise test expected to fail"
    )
    create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=30.0,
        max_cld_rtn_days=2555,
        max_onprem_dly_prtctd_data=100.0,
        max_onprem_rtn_days=1095,
        additional_ds_name=additional_ds_name,
        additional_ds_required=True,
        verify_deploy_state=True,
    )
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AwsStorageLocation.AWS_US_WEST_2)
    assign_protection_template_to_vm(context)
    run_backup(context, backup_type=BackupTypeScheduleIDs.cloud)


@mark.order(205)
@mark.deploy
def test_deploy_psgw_with_morethan_max_capacity_using_sizer(context):
    """TestRail ID: C57582224
    Validate PSGW deployment with morethan supported capacity using sizer params
    """
    vc_name = context.vcenter_name.split(".")
    array_name = context.array.split(".")
    additional_ds_name = f"{vc_name[0]}-{array_name[0]}-PSG-DS"
    logger.warning(
        f"We need to create datastores to accomodate psgw capacity and datastore name must contains: {additional_ds_name} on vCenter: {context.vcenter_name} otherwise test expected to fail"
    )
    response = create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=30.0,
        max_cld_rtn_days=2555,
        max_onprem_dly_prtctd_data=101.0,
        max_onprem_rtn_days=1095,
        return_response=True,
        additional_ds_name=additional_ds_name,
        additional_ds_required=True,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_ONPREM_DAILY_PROTECTED_DATA,
    )
