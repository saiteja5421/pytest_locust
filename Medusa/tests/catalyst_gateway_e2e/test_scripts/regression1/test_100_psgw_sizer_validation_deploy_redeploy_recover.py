"""
TestRail ID - C57582211
    verify on create PSGW wizard Estimate step should be replaced with size step and validate, size wizard is listing proper vCpu, Memory, Storage Capacity and Storage iops values based on the inputs provided.

TestRail ID - C57582213
    Validate the create PSGW, size wizard moderate values for "maxInCloudDailyProtectedDataInTiB",
    "maxInCloudRetentionDays", "maxOnPremDailyProtectedDataInTiB", "maxOnPremRetentionDays"
    
TestRail ID - C57582214
    Validate create PSGW, size wizard error cases for "maxInCloudDailyProtectedDataInTiB",
    "maxInCloudRetentionDays", "maxOnPremDailyProtectedDataInTiB", "maxOnPremRetentionDays"

TestRail ID - C57582215
    Execute the size wizard error cases tests together and observe the behavior of Required resources (such as vCpu, Memory, Storage Capacity and Storage iops)

TestRail ID - C57582217
    Deploy a PSG with latest PSG changes (includes Size step )

TestRail ID - C57582218
    Deploy a PSG with latest PSG changes (includes Size step ) and validate protection work flow.

TestRail ID - C57582219
    Validate required resources of a PSGW after successful deployment

TestRail ID - C57581935: 
    Deploy protection store gateway VM on a registered vcenter where OPE is deployed

TestRail ID - C57581972:
    Deploy protection store gateway VM, with the same name on a registered vcenter where OPE is deployed

TestRail ID - C57582138, C57582158, C57582174:
    1. Recover a PSG into the same vCenter
    2. Recover a PSG with same IPv4
    3. Recover protetion store gateway with sizer fields and restore existing cloud backup that were created before recover
"""

import logging
from time import sleep
from requests import codes

from pytest import fixture, mark
from lib.common.enums.psg import HealthState, HealthStatus, State
from lib.common.error_messages import (
    ERROR_MESSAGE_CLOUD_DAILY_PROTECTED_DATA,
    ERROR_MESSAGE_INVALID_CLOUD_PRTCTD_DATA_FIELD_STRING,
    ERROR_MESSAGE_CLOUD_RETENTION_DAYS,
    ERROR_MESSAGE_INVALID_CLOUD_RTN_FIELD_STRING,
    ERROR_MESSAGE_INVALID_CLOUD_RTN_FIELD_FLOAT,
    ERROR_MESSAGE_ONPREM_DAILY_PROTECTED_DATA,
    ERROR_MESSAGE_INVALID_ONPREM_PRTCTD_DATA_FIELD_STRING,
    ERROR_MESSAGE_ONPREM_RETENTION_DAYS,
    ERROR_MESSAGE_INVALID_ONPREM_RTN_FIELD_STRING,
    ERROR_MESSAGE_INVALID_ONPREM_RTN_FIELD_FLOAT,
)
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    validate_psgw_error_messages,
    select_or_create_protection_store_gateway_vm,
    delete_protection_store_gateway_vm_from_vcenter,
    wait_for_psg,
    recover_protection_store_gateway_vm,
    validate_psgw_resources_post_update,
    validate_psgw_sizer_fields,
    validate_psgw_sizer_fields_error_messages,
)
from tests.steps.vm_protection.backup_steps import (
    run_backup,
    restore_virtual_machine,
)
from tests.steps.vm_protection.protection_template_steps import (
    create_protection_template,
    assign_protection_template_to_vm,
)

from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from lib.common.enums.restore_type import RestoreType
from lib.common.enums.aws_regions import AwsStorageLocation
from tests.catalyst_gateway_e2e.test_context import Context
from lib.common.error_messages import ERROR_MESSAGE_NAME_NOT_UNIQUE

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context(v_center_type="VCENTER2")
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(test_context)
    logger.info("Teardown Complete".center(20, "*"))


@mark.deploy
@mark.order(100)
def test_valildate_create_psgw_moderate_size_fields(context):
    """TestRail ID - C57582211
        verify on create PSGW wizard Estimate step should be replaced with size step and validate, size wizard is listing proper vCpu, Memory, Storage Capacity and Storage iops values based on the inputs provided.

    TestRail ID - C57582213
        Validate the create PSGW, size wizard moderate values for "maxInCloudDailyProtectedDataInTiB",
        "maxInCloudRetentionDays", "maxOnPremDailyProtectedDataInTiB", "maxOnPremRetentionDays"
    """
    validate_psgw_sizer_fields(
        context,
        get_create_psgw_sizer=True,
        max_cld_dly_prtctd_data=10,
        max_cld_rtn_days=999,
        max_onprem_dly_prtctd_data=38.0,
        max_onprem_rtn_days=500,
        exp_required_fields={
            "vCpu": 16,
            "ramInGiB": 32,
            "iops": 1000,
            "storageInTiB": 77,
            "bandwidthMegabitsPerSecond": 153,
        },
    )
    validate_psgw_sizer_fields(
        context,
        get_create_psgw_sizer=True,
        max_cld_dly_prtctd_data=25,
        max_cld_rtn_days=2000,
        max_onprem_dly_prtctd_data=78.0,
        max_onprem_rtn_days=1000,
        exp_required_fields={
            "vCpu": 32,
            "ramInGiB": 64,
            "iops": 2000,
            "storageInTiB": 198,
            "bandwidthMegabitsPerSecond": 382,
        },
    )


@mark.deploy
@mark.order(105)
def test_valildate_create_psgw_size_fields_error_cases(context):
    """TestRail ID - C57582214
        Validate create PSGW, size wizard error cases for "maxInCloudDailyProtectedDataInTiB",
        "maxInCloudRetentionDays", "maxOnPremDailyProtectedDataInTiB", "maxOnPremRetentionDays"

    TestRail ID - C57582215
        Execute the size wizard error cases tests together and observe the behavior of Required resources (such as vCPU, Memory, Storage Capacity and Storage iops)
    """
    logger.info("***Validating max cloud daily protected data field error messages***")
    validate_psgw_sizer_fields_error_messages(
        context,
        validate_create_psgw_sizer=True,
        max_cld_dly_prtctd_data=0,
        exp_error_msg=ERROR_MESSAGE_CLOUD_DAILY_PROTECTED_DATA,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        validate_create_psgw_sizer=True,
        max_cld_dly_prtctd_data=31,
        exp_error_msg=ERROR_MESSAGE_CLOUD_DAILY_PROTECTED_DATA,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        validate_create_psgw_sizer=True,
        max_cld_dly_prtctd_data="string",
        exp_error_msg=ERROR_MESSAGE_INVALID_CLOUD_PRTCTD_DATA_FIELD_STRING,
    )
    logger.info("***Successfully validated max cloud daily protected data field error messages***")
    logger.info("***Validating max cloud retention field error messages***")
    validate_psgw_sizer_fields_error_messages(
        context,
        validate_create_psgw_sizer=True,
        max_cld_rtn_days=0,
        exp_error_msg=ERROR_MESSAGE_CLOUD_RETENTION_DAYS,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        validate_create_psgw_sizer=True,
        max_cld_rtn_days=3651,
        exp_error_msg=ERROR_MESSAGE_CLOUD_RETENTION_DAYS,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        validate_create_psgw_sizer=True,
        max_cld_rtn_days="string",
        exp_error_msg=ERROR_MESSAGE_INVALID_CLOUD_RTN_FIELD_STRING,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        validate_create_psgw_sizer=True,
        max_cld_rtn_days=10.0,
        exp_error_msg=ERROR_MESSAGE_INVALID_CLOUD_RTN_FIELD_FLOAT,
    )
    logger.info("***Successfully validated max cloud retention field error messages***")
    logger.info("***Validating max onprem daily protected data field error messages***")
    validate_psgw_sizer_fields_error_messages(
        context,
        validate_create_psgw_sizer=True,
        max_onprem_dly_prtctd_data=0,
        exp_error_msg=ERROR_MESSAGE_ONPREM_DAILY_PROTECTED_DATA,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        validate_create_psgw_sizer=True,
        max_onprem_dly_prtctd_data=101,
        exp_error_msg=ERROR_MESSAGE_ONPREM_DAILY_PROTECTED_DATA,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        validate_create_psgw_sizer=True,
        max_onprem_dly_prtctd_data="string",
        exp_error_msg=ERROR_MESSAGE_INVALID_ONPREM_PRTCTD_DATA_FIELD_STRING,
    )
    logger.info("***Successfully validated max onprem daily protected data field error messages***")
    logger.info("***Validating max onprem retention field error messages***")
    validate_psgw_sizer_fields_error_messages(
        context,
        validate_create_psgw_sizer=True,
        max_onprem_rtn_days=0,
        exp_error_msg=ERROR_MESSAGE_ONPREM_RETENTION_DAYS,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        validate_create_psgw_sizer=True,
        max_onprem_rtn_days=2556,
        exp_error_msg=ERROR_MESSAGE_ONPREM_RETENTION_DAYS,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        validate_create_psgw_sizer=True,
        max_onprem_rtn_days="string",
        exp_error_msg=ERROR_MESSAGE_INVALID_ONPREM_RTN_FIELD_STRING,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        validate_create_psgw_sizer=True,
        max_onprem_rtn_days=12.90,
        exp_error_msg=ERROR_MESSAGE_INVALID_ONPREM_RTN_FIELD_FLOAT,
    )
    logger.info("***Successfully validated max onprem retention field error messages***")


@mark.order(110)
@mark.deploy
def test_validate_deploy_psgw_on_do_hosted_vc(context, vm_deploy):
    """TestRail ID - C57581935:
        Deploy protection store gateway VM on a registered vcenter where OPE is deployed
    TestRail ID - C57582217
        Deploy a PSG with latest PSG changes (includes Size step )

    TestRail ID - C57582218
        Deploy a PSG with latest PSG changes (includes Size step ) and validate protection work flow.

    TestRail ID - C57582219
        Validate required resources of a PSGW after successful deployment
    """
    do_hosted_vc = context.test_data["do_hosted_vc"]
    logger.warning(
        f"Data Orchestrator 'DO' should be deployed on the vCenter: {do_hosted_vc}, otherwise intention of this test will be deviated..."
    )
    assert (
        context.vcenter_name == do_hosted_vc
    ), f"Failed to deploy the PSGW, VC: {context.vcenter_name} and do hosted VC: {do_hosted_vc} doesn't matached"
    logger.info(f"Running the test against to the VC: {context.vcenter_name} and do hosted vc: {do_hosted_vc}")
    max_cld_dly_prtctd_data = 2.0
    max_cld_rtn_days = 199
    max_onprem_dly_prtctd_data = 5.0
    max_onprem_rtn_days = 99
    create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )
    validate_protection_store_gateway_vm(context)
    validate_psgw_resources_post_update(
        context,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )
    create_protection_template(context, cloud_region=AwsStorageLocation.AWS_US_WEST_2)
    assign_protection_template_to_vm(context)
    run_backup(context, backup_type=BackupTypeScheduleIDs.cloud)
    restore_virtual_machine(context, RestoreType.new, "local")


@mark.order(115)
@mark.deploy
def test_validate_psgw_deployment_with_same_name(context):
    """TestRail ID - C57581972:
    Deploy protection store gateway VM, with the same name on a registered vcenter where OPE is deployed
    """
    select_or_create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=2.0,
        max_cld_rtn_days=199,
        max_onprem_dly_prtctd_data=5.0,
        max_onprem_rtn_days=99,
    )
    response = create_protection_store_gateway_vm(
        context,
        return_response=True,
        same_psgw_name=True,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_NAME_NOT_UNIQUE,
    )


@mark.order(120)
@mark.recover
def test_recover_psg_happy_path(context, vm_deploy):
    """TestRail ID - C57582138, C57582158, C57582174:
    1. Recover a PSG into the same vCenter
    2. Recover a PSG with same IPv4
    3. Recover protetion store gateway with sizer fields and restore existing cloud backup that were created before recover
    """
    max_cld_dly_prtctd_data = 2.0
    max_cld_rtn_days = 199
    max_onprem_dly_prtctd_data = 5.0
    max_onprem_rtn_days = 99
    select_or_create_protection_store_gateway_vm(
        context,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AwsStorageLocation.AWS_US_WEST_2)
    assign_protection_template_to_vm(context)
    run_backup(context, backup_type=BackupTypeScheduleIDs.cloud)

    # Delete PSG VM from vCenter to simulate PSG disaster
    delete_protection_store_gateway_vm_from_vcenter(context, force=True)

    # Wait for PSG state become Unknown and health state/status become Unknown/Disconnecte
    wait_for_psg(
        context, state=State.UNKNOWN, health_state=HealthState.UNKNOWN, health_status=HealthStatus.DISCONNECTED
    )

    # As per the design, PSG Cloud stores needs 15 minutes of idle time before we attempt to "/recover"
    logger.info("PSG Cloud store needs 15min of idle time before attempting '/recover' operation. Sleeping 15mins")
    sleep(15 * 60)

    # Recover PSG VM with same sizer fields that we used for deploy
    recover_protection_store_gateway_vm(
        context,
        recover_psgw_name=f"recover_{context.psgw_name}",
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )
    validate_protection_store_gateway_vm(context)
    validate_psgw_resources_post_update(
        context,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )

    # Restore cloud backup, that was existed before recover
    restore_virtual_machine(context, RestoreType.new, "cloud")
