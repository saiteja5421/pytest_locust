"""
Sanity test to performs the following workflow:

    1. Deploy PSG in the provided vCenter
    2. Create Policy using the PSG created in step 1
    3. Run backups and check metrics (before/after)
    4. Edit Network settings like IP, Proxy, NTP, DNS
    5. Validate Resize PSGW functionality
    6. Run backups and check metrics (before/after)
    7. Run Restores (Same and New)7. 
    8. Delete backups and check metrics (before/after)
    9. Delete policy and PSG

"""

import logging

from pytest import fixture, mark
from lib.common.enums.azure_locations import AzureLocations
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
    validate_protection_store_gateway_vm_ok_state_and_station_id,
    validate_psg_networking_settings,
    validate_existing_psgw_resize_functionality,
    validate_psgw_resources_post_update,
)

from tests.steps.vm_protection.backup_steps import (
    run_backup_and_check_usage,
    restore_virtual_machine,
    delete_backup_and_check_usage,
    delete_all_backups,
)
from tests.steps.vm_protection.protection_template_steps import (
    assign_protection_template_to_vm,
    create_protection_template,
    delete_unassinged_protection_policy,
    unassign_protecion_policy_from_vm,
)
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.audit.audit_events_steps import verify_protection_policy_create_audit_event
from tests.catalyst_gateway_e2e.test_context import SanityContext
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.common.enums.restore_type import RestoreType
from lib.common.enums.backup_type_param import BackupTypeParam

global TOTAL_PASS

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = SanityContext(set_static_policy=False, deploy=True)
    test_context.backups_taken = 0
    global TOTAL_PASS
    TOTAL_PASS = 0
    yield test_context
    if TOTAL_PASS != 15:
        logger.info(f"Skipping teardown as all test cases not passed. Total passed: {TOTAL_PASS}")
    else:
        logger.info(f"\n{'Teardown Start'.center(40, '*')}")
        perform_cleanup(test_context, clean_vm=True)
        logger.info(f"\n{'Teardown Complete'.center(40, '*')}")


@mark.full
@mark.order(100)
@mark.dependency(name="test_deploy_psgvm", scope="module")
def test_deploy_psgvm(context, vm_deploy):
    # Check if we need additional DATA interface. Todo: Have to confirm and
    # convert all flat network vcsa/array to non-flat
    additional_interface = True
    if "flat_network_support" in context.vcenter and context.vcenter["flat_network_support"] == "yes":
        additional_interface = False
    create_protection_store_gateway_vm(context, add_data_interface=additional_interface)
    validate_protection_store_gateway_vm(context)
    validate_protection_store_gateway_vm_ok_state_and_station_id(context)
    global TOTAL_PASS
    TOTAL_PASS += 1


@mark.full
@mark.order(200)
@mark.dependency(name="test_create_protection_policy", depends=["test_deploy_psgvm"], scope="module")
def test_create_protection_policy(context):
    create_protection_template(context, cloud_region=AzureLocations.AZURE_eastus2)
    global TOTAL_PASS
    TOTAL_PASS += 1


@mark.full
@mark.order(300)
@mark.dependency(
    name="test_assign_protection_policy",
    depends=["test_create_protection_policy"],
    scope="module",
)
def test_assign_protection_policy(context):
    assign_protection_template_to_vm(context, backup_granularity_type="VOLUME")
    global TOTAL_PASS
    TOTAL_PASS += 1


@mark.full
@mark.order(310)
@mark.dependency(depends=["test_create_protection_policy"])
def test_verify_protection_policy_create_audit_log(context):
    verify_protection_policy_create_audit_event(context_user=context.user, policy_name=context.local_template)
    global TOTAL_PASS
    TOTAL_PASS += 1


@mark.full
@mark.order(400)
@mark.dependency(
    name="test_run_backup_take_metrics",
    depends=["test_assign_protection_policy"],
    scope="module",
)
def test_run_backup_take_metrics(context):
    run_backup_and_check_usage(context)
    context.backups_taken += 1
    global TOTAL_PASS
    TOTAL_PASS += 1


@mark.full
@mark.order(500)
@mark.dependency(name="test_edit_network", depends=["test_deploy_psgvm"], scope="module")
def test_edit_network(context):
    validate_psg_networking_settings(context)
    global TOTAL_PASS
    TOTAL_PASS += 1


@mark.full
@mark.order(550)
@mark.dependency(depends=["test_deploy_psgvm"])
def test_valildate_resize_psgw_functionality(context):
    max_cld_dly_prtctd_data = 10.0
    max_cld_rtn_days = 200
    max_onprem_dly_prtctd_data = 15.0
    max_onprem_rtn_days = 250
    validate_existing_psgw_resize_functionality(
        context,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )
    validate_psgw_resources_post_update(
        context,
        max_cld_dly_prtctd_data=max_cld_dly_prtctd_data,
        max_cld_rtn_days=max_cld_rtn_days,
        max_onprem_dly_prtctd_data=max_onprem_dly_prtctd_data,
        max_onprem_rtn_days=max_onprem_rtn_days,
    )
    global TOTAL_PASS
    TOTAL_PASS += 1


@mark.full
@mark.order(600)
@mark.dependency(
    name="test_run_backup_take_metrics_again",
    scope="module",
    depends=["test_create_protection_policy", "test_edit_network"],
)
def test_run_backup_take_metrics_again(context):
    run_backup_and_check_usage(context)
    context.backups_taken += 1
    global TOTAL_PASS
    TOTAL_PASS += 1


@mark.full
@mark.order(700)
@mark.dependency(
    name="test_restore_vm_from_local_backups",
    scope="module",
    depends=["test_run_backup_take_metrics", "test_edit_network"],
)
def test_restore_vm_from_local_backups(context):
    restore_virtual_machine(context, RestoreType.new, "local")
    restore_virtual_machine(context, RestoreType.existing, "local", quite_time=120)
    global TOTAL_PASS
    TOTAL_PASS += 1


@mark.full
@mark.order(800)
@mark.dependency(
    name="test_restore_vm_from_cloud_backups",
    scope="module",
    depends=["test_run_backup_take_metrics", "test_edit_network"],
)
def test_restore_vm_from_cloud_backups(context):
    header_with_new_token = SanityContext(set_static_policy=False, deploy=True).user.regenerate_header()
    context.user.authentication_header = header_with_new_token
    restore_virtual_machine(context, RestoreType.new, "cloud")
    restore_virtual_machine(context, RestoreType.existing, "cloud", quite_time=120)
    global TOTAL_PASS
    TOTAL_PASS += 1


@mark.full
@mark.order(900)
@mark.dependency(name="test_create_aws_protection_policy", depends=["test_deploy_psgvm"], scope="module")
def test_create_aws_protection_policy(context):
    unassign_protecion_policy_from_vm(context)
    delete_unassinged_protection_policy(context)
    create_protection_template(context, cloud_region=AwsStorageLocation.AWS_AP_NORTHEAST_2)
    global TOTAL_PASS
    TOTAL_PASS += 1


@mark.full
@mark.order(910)
@mark.dependency(
    name="test_assign_aws_protection_policy",
    depends=["test_create_aws_protection_policy"],
    scope="module",
)
def test_assign_aws_protection_policy(context):
    assign_protection_template_to_vm(context, backup_granularity_type="VOLUME")
    global TOTAL_PASS
    TOTAL_PASS += 1


@mark.full
@mark.order(915)
@mark.dependency(
    name="test_aws_run_backup_take_metrics",
    depends=["test_assign_aws_protection_policy"],
    scope="module",
)
def test_aws_run_backup_take_metrics(context):
    run_backup_and_check_usage(context, multiple_stores=True)
    context.backups_taken += 1
    global TOTAL_PASS
    TOTAL_PASS += 1


@mark.full
@mark.order(920)
@mark.dependency(
    name="test_restore_vm_from_cloud_backups_aws",
    scope="module",
    depends=["test_aws_run_backup_take_metrics"],
)
def test_restore_vm_from_cloud_backups_aws(context):
    header_with_new_token = SanityContext(set_static_policy=False, deploy=True).user.regenerate_header()
    context.user.authentication_header = header_with_new_token
    restore_virtual_machine(context, RestoreType.new, "cloud")
    restore_virtual_machine(context, RestoreType.existing, "cloud", quite_time=120)
    global TOTAL_PASS
    TOTAL_PASS += 1


@mark.full
@mark.order(925)
@mark.dependency(
    name="test_aws_delete_backups",
    scope="module",
    depends=["test_aws_run_backup_take_metrics", "test_run_backup_take_metrics"],
)
def test_delete_backups(context):
    delete_backup_and_check_usage(context, backups_taken=context.backups_taken)
    delete_all_backups(BackupTypeParam.snapshots, context)
    global TOTAL_PASS
    TOTAL_PASS += 1
