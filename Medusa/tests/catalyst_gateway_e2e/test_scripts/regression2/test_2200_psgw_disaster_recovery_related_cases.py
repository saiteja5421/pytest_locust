"""
TestRail ID - C57582138, C57582158, C57582174:
    Recover a PSG into the same vCenter
    Recover a PSG with same IPv4
    Validate-PSGW-recover-size-wizard-moderate-required-field-values

TestRail ID - C57582140:
    Recover a PSG and restore an asset from its cloud backup

TestRail ID - C57582159:
    Recover a PSG with invalid IPv4
    
TestRail ID - C57582148	
     Perform action - 'Shutdown' on the recovered PSG

TestRail ID - C57582149	
    Perform action - 'Power On' on the recovered PSG

TestRail ID - C57582150	
    Perform action - 'Remote Support' on the recovered PSG	
    
TestRail ID - C57582151
    Perform action - 'Generate Support Bundle' on the recovered PSG
    
TestRail ID - C57582152
    Perform action - 'Reveal Console Password' on the recovered PSG

TestRail ID - C57582156	:
    Recover a healthy state PSG

TestRail ID - C57582155	:
    Recover a PSG with the same name to same vCenter

TestRail ID - C57582141 
    Recover a PSG contains multiple cloud store

TestRail ID - C57582143
    Recover PSG back to back with multiple cloud store

TestRail ID - C57582154:
    Monitor local/cloud store usage of recovered PSG

TestRail ID - C57582163	:
    Unregister vCenter when recovered PSG contains few local/cloud backups
    
TestRail ID - C57582161	:
    Delete recovered PSG whose VM removed from the vCenter

TestRail ID - C57582162:
    Delete recovered PSG when it contains few local/cloud backups

TestRail ID - C57582207
    Validate-PSGW-Sizer-fields-override-functionality

TestRail ID - C57582208	:
    Validate-PSGW-error-cases-for-override-flag

TestRail ID - C57582144:
    Modify network interface settings of recovered PSG
"""

import random
import time
import logging
from pytest import fixture, mark
from requests import codes
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.common.enums.azure_locations import AzureLocations
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from lib.common.enums.network_interface_type import NetworkInterfaceType
from lib.common.enums.psg import HealthState, HealthStatus, State
from tests.steps.vm_protection.common_steps import perform_cleanup
from tests.steps.vm_protection.protection_template_steps import (
    create_protection_template,
    assign_protection_template_to_vm,
    create_protection_template_with_multiple_cloud_regions,
    delete_unassinged_protection_policy,
    unassign_protecion_policy_from_all_vms,
)
from tests.steps.vm_protection.backup_steps import (
    run_backup,
    restore_virtual_machine,
    run_backup_and_check_usage,
    delete_backup_and_check_usage,
)
from tests.steps.vm_protection.vcenter_steps import (
    unregister_vcenter,
    add_vcenter,
)
from lib.common.error_messages import (
    ERROR_MESSAGE_OVERRIDE_CPU,
    ERROR_MESSAGE_OVERRIDE_RAM,
    ERROR_MESSAGE_OVERRIDE_STORAGE,
    ERROR_MESSAGE_RECOVER_PSGW_WITH_INVALID_IP,
    ERROR_MESSAGE_RECOVER_OK_CONNECTED_PSG,
    ERROR_MESSAGE_CREATE_PSG_VM_EXISTS,
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
from tests.steps.vm_protection.psgw_steps import (
    add_additional_network_interface_catalyst_gateway_vm,
    create_protection_store_gateway_vm,
    delete_network_interface_catalyst_gateway_vm,
    validate_protection_store_gateway_vm,
    recover_protection_store_gateway_vm,
    delete_protection_store_gateway_vm_from_vcenter,
    validate_psg_networking_settings,
    wait_for_psg,
    wait_to_get_psgw_to_powered_off,
    wait_for_psgw_to_power_on_and_connected,
    remote_support_enable_and_disable_on_psgw,
    generate_support_bundle_for_psgw,
    reveal_console_password_on_the_recovered_psgw,
    validate_psgw_sizer_fields_error_messages,
    delete_protection_store_gateway_vm,
    verify_delete_psgw_not_allowed_if_backup_exists,
    select_or_create_protection_store_gateway_vm,
    validate_psgw_error_messages,
    validate_ssh_login_through_console_password,
)
from lib.common.enums.restore_type import RestoreType
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.api.catalyst_gateway import CatalystGateway
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
TestRail ID - C57582138, C57582158, C57582174, C57582207:
    Recover a PSG into the same vCenter
    Recover a PSG with same IPv4
    Validate-PSGW-recover-size-wizard-moderate-required-field-values
    Validate-PSGW-Sizer-fields-override-functionality
"""


@mark.order(2200)
@mark.recover
@mark.deploy
@mark.dependency()
def test_recover_psg_happy_path(context, vm_deploy):
    create_protection_store_gateway_vm(
        context,
    )
    validate_protection_store_gateway_vm(context)
    create_protection_template(context, cloud_region=AwsStorageLocation.AWS_EU_WEST_2)
    assign_protection_template_to_vm(context)
    run_backup(context)

    # Delete PSG VM from vCenter to simulate PSG disaster
    delete_protection_store_gateway_vm_from_vcenter(context, force=True)

    # Wait for PSG state become Unknown and health state/status become Unknown/Disconnecte
    wait_for_psg(
        context, state=State.UNKNOWN, health_state=HealthState.UNKNOWN, health_status=HealthStatus.DISCONNECTED
    )

    # As per the design, PSG Cloud stores needs 15 minutes of idle time before we attempt to "/recover"
    logger.info("PSG Cloud store needs 15min of idle time before attempting '/recover' operation. Sleeping 15mins")
    time.sleep(15 * 60)

    # Recover PSG VM with override
    recover_psgw_name = f"recover_{context.psgw_name}"
    recover_protection_store_gateway_vm(
        context,
        recover_psgw_name=recover_psgw_name,
        override_cpu=8,
        override_ram_gib=26,
        override_storage_tib=13,
    )

    # Perform asset backup should work well with existing local/cloud stores and also the protection policy
    validate_protection_store_gateway_vm(context)
    run_backup(context)


"""
TestRail ID - C57582144:
    Modify network interface settings of recovered PSG
"""


@mark.order(2205)
@mark.recover
@mark.dependency(depends=["test_recover_psg_happy_path"])
def test_update_dns_ntp_proxy_primary_add_remove_data_interface_post_recovery(context):
    # Delete DATA interface (Data1)
    atlas = CatalystGateway(context.user)
    psgw = atlas.get_catalyst_gateway_by_name(context.psgw_name)
    network_address = context.nic_data1_ip
    nic_id = atlas.get_network_interface_id_by_network_address(psgw["id"], network_address)
    if nic_id is not None:
        delete_network_interface_catalyst_gateway_vm(context, network_address)
    else:
        delete_network_interface_catalyst_gateway_vm(context, context.nic_data1["additional_network_address1"])
    # Add additonal DATA interface (Data1)
    add_additional_network_interface_catalyst_gateway_vm(context, NetworkInterfaceType.data1)
    # Verify DNS, NTP, Proxy and Primary network interface(IE. 'Network 1')
    logger.info("Updating DNS, NTP, Proxy and Primary NIC Interface ")
    validate_psg_networking_settings(context)
    logger.info("waiting for 10 minutest after updating n/w details.")
    time.sleep(600)
    # Post modification of PSG network config verify backup works as expected
    run_backup(context)


"""
TestRail ID - C57582175:
    Validate-PSGW-recover-size-wizard-required-field-error-cases
"""


@mark.order(2210)
@mark.recover
@mark.dependency(depends=["test_recover_psg_happy_path"])
def test_valildate_recovered_psgw_size_fields_error_cases(context):
    logger.info("***Validating max cloud daily protected data field error messages***")
    validate_psgw_sizer_fields_error_messages(
        context,
        max_cld_dly_prtctd_data=0,
        exp_error_msg=ERROR_MESSAGE_CLOUD_DAILY_PROTECTED_DATA,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_cld_dly_prtctd_data=31,
        exp_error_msg=ERROR_MESSAGE_CLOUD_DAILY_PROTECTED_DATA,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_cld_dly_prtctd_data="string",
        exp_error_msg=ERROR_MESSAGE_INVALID_CLOUD_PRTCTD_DATA_FIELD_STRING,
    )
    logger.info("***Successfully validated max cloud daily protected data field error messages***")
    logger.info("***Validating max cloud retention field error messages***")
    validate_psgw_sizer_fields_error_messages(
        context,
        max_cld_rtn_days=0,
        exp_error_msg=ERROR_MESSAGE_CLOUD_RETENTION_DAYS,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_cld_rtn_days=3651,
        exp_error_msg=ERROR_MESSAGE_CLOUD_RETENTION_DAYS,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_cld_rtn_days="string",
        exp_error_msg=ERROR_MESSAGE_INVALID_CLOUD_RTN_FIELD_STRING,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_cld_rtn_days=10.0,
        exp_error_msg=ERROR_MESSAGE_INVALID_CLOUD_RTN_FIELD_FLOAT,
    )
    logger.info("***Successfully validated max cloud retention field error messages***")
    logger.info("***Validating max onprem daily protected data field error messages***")
    validate_psgw_sizer_fields_error_messages(
        context,
        max_onprem_dly_prtctd_data=0,
        exp_error_msg=ERROR_MESSAGE_ONPREM_DAILY_PROTECTED_DATA,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_onprem_dly_prtctd_data=101,
        exp_error_msg=ERROR_MESSAGE_ONPREM_DAILY_PROTECTED_DATA,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_onprem_dly_prtctd_data="string",
        exp_error_msg=ERROR_MESSAGE_INVALID_ONPREM_PRTCTD_DATA_FIELD_STRING,
    )
    logger.info("***Successfully validated max onprem daily protected data field error messages***")
    logger.info("***Validating max onprem retention field error messages***")
    validate_psgw_sizer_fields_error_messages(
        context,
        max_onprem_rtn_days=0,
        exp_error_msg=ERROR_MESSAGE_ONPREM_RETENTION_DAYS,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_onprem_rtn_days=2556,
        exp_error_msg=ERROR_MESSAGE_ONPREM_RETENTION_DAYS,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_onprem_rtn_days="string",
        exp_error_msg=ERROR_MESSAGE_INVALID_ONPREM_RTN_FIELD_STRING,
    )
    validate_psgw_sizer_fields_error_messages(
        context,
        max_onprem_rtn_days=12.90,
        exp_error_msg=ERROR_MESSAGE_INVALID_ONPREM_RTN_FIELD_FLOAT,
    )
    logger.info("***Successfully validated max onprem retention field error messages***")


"""
TestRail ID - C57582140:
    Recover a PSG and restore an asset from its cloud backup
"""


@mark.order(2215)
@mark.recover
@mark.dependency(depends=["test_recover_psg_happy_path"])
def test_restore_cloud_backup_from_recoverd_psgw(context):
    # Restore VM from cloud backup using recovered psgw
    restore_virtual_machine(context, RestoreType.existing, "cloud")


"""
TestRail ID - C57582162:
    Delete recovered PSG when it contains few local/cloud backups
"""


@mark.order(2220)
@mark.recover
@mark.dependency(depends=["test_recover_psg_happy_path"])
def test_delete_recovered_psg_contains_local_cloud_backups(context):
    verify_delete_psgw_not_allowed_if_backup_exists(context)


"""
TestRail ID - C57582154:
    Monitor local/cloud store usage of recovered PSG
"""


@mark.order(2225)
@mark.recover
@mark.dependency(depends=["test_recover_psg_happy_path"])
def test_monitor_local_cloud_storage(context):
    run_backup_and_check_usage(context)
    delete_backup_and_check_usage(context)


"""
TestRail ID - C57582159:
    Recover a PSG with invalid IPv4
"""


@mark.order(2230)
@mark.recover
@mark.dependency(depends=["test_recover_psg_happy_path"])
def test_recover_psgw_with_invalid_ip(context):
    old_network_ip = context.network
    context.network = "192.21.150.132"
    response = recover_protection_store_gateway_vm(
        context,
        recover_psgw_name=f"recover_{context.psgw_name}_error",
        return_response=True,
    )
    context.network = old_network_ip
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_RECOVER_PSGW_WITH_INVALID_IP,
    )


"""
TestRail ID - C57582148
     Perform action - 'Shutdown' on the recovered PSG
"""


@mark.order(2235)
@mark.recover
@mark.dependency(depends=["test_recover_psg_happy_path"])
def test_shutdown_on_the_recovered_psgw(context):
    # Shutdown the recovered psgw
    wait_to_get_psgw_to_powered_off(context)


"""
TestRail ID - C57582149
    Perform action - 'Power On' on the recovered PSG
"""


@mark.order(2240)
@mark.recover
@mark.dependency(depends=["test_shutdown_on_the_recovered_psgw"])
def test_power_on_the_recovered_psgw(context):
    # PowerOn the recovered psgw
    wait_for_psgw_to_power_on_and_connected(context)


"""
TestRail ID - C57582208	:
    Validate-PSGW-error-cases-for-override-flag
"""


@mark.order(2245)
@mark.recover
@mark.dependency(depends=["test_power_on_the_recovered_psgw"])
def test_validate_error_cases_for_override_on_recover(context):
    logger.info("***Validating min. cpu on override error messages***")
    response = recover_protection_store_gateway_vm(
        context,
        recover_psgw_name=f"recover_{context.psgw_name}_error",
        override_cpu=1,
        override_ram_gib=24,
        override_storage_tib=1,
        return_response=True,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_OVERRIDE_CPU,
    )
    logger.info("***Successfully validated  min. cpu on override error messages***")
    logger.info("***Validating max. cpu on override error messages***")
    response = recover_protection_store_gateway_vm(
        context,
        recover_psgw_name=f"recover_{context.psgw_name}_error",
        override_cpu=random.randint(49, 100),
        override_ram_gib=24,
        override_storage_tib=1,
        return_response=True,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_OVERRIDE_CPU,
    )
    logger.info("***Successfully validated  max. cpu on override error messages***")
    logger.info("***Validating min. ram on override error messages***")
    response = recover_protection_store_gateway_vm(
        context,
        recover_psgw_name=f"recover_{context.psgw_name}_error",
        override_cpu=8,
        override_ram_gib=random.randint(0, 15),
        override_storage_tib=1,
        return_response=True,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_OVERRIDE_RAM,
    )
    logger.info("***Successfully validated  min. ram on override error messages***")
    logger.info("***Validating max. ram on override error messages***")
    response = recover_protection_store_gateway_vm(
        context,
        recover_psgw_name=f"recover_{context.psgw_name}_error",
        override_cpu=8,
        override_ram_gib=random.randint(501, 1000),
        override_storage_tib=1,
        return_response=True,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_OVERRIDE_RAM,
    )
    logger.info("***Successfully validated  max. ram on override error messages***")
    logger.info("***Validating min. storage on override error messages***")
    response = recover_protection_store_gateway_vm(
        context,
        recover_psgw_name=f"recover_{context.psgw_name}_error",
        override_cpu=8,
        override_ram_gib=24,
        override_storage_tib=0,
        return_response=True,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_OVERRIDE_STORAGE,
    )
    logger.info("***Successfully validated  min. storage on override error messages***")
    logger.info("***Validating max. storage on override error messages***")
    response = recover_protection_store_gateway_vm(
        context,
        recover_psgw_name=f"recover_{context.psgw_name}_error",
        override_cpu=8,
        override_ram_gib=24,
        override_storage_tib=random.randint(501, 1000),
        return_response=True,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_OVERRIDE_STORAGE,
    )
    logger.info("***Successfully validated max. storage on override error messages***")


"""
TestRail ID - C57582150
    Perform action - 'Remote Support' on the recovered PSG
"""


@mark.order(2250)
@mark.recover
@mark.dependency(depends=["test_power_on_the_recovered_psgw"])
def test_remote_support_on_the_recovered_psgw(context):
    # Enable the remote support in the recovered psgw
    remote_support_enable_and_disable_on_psgw(
        context,
        remote_support_enable=True,
    )


"""
TestRail ID - C57582151
    Perform action - 'Generate Support Bundle' on the recovered PSG
"""


@mark.order(2255)
@mark.recover
@mark.dependency(depends=["test_remote_support_on_the_recovered_psgw"])
def test_generate_support_bundle_on_the_recovered_psgw(context):
    # Generate the support bundle in the recovered psgw
    generate_support_bundle_for_psgw(
        context,
        support_bundle_slim=True,
    )


"""
TestRail ID - C57582152
    Perform action - 'Reveal Console Password' on the recovered PSG
"""


@mark.order(2260)
@mark.recover
@mark.dependency(depends=["test_recover_psg_happy_path"])
def test_reveal_console_password_on_the_recovered_psgw(context):
    # Reveal console password in the recovered psgw
    reveal_console_password = reveal_console_password_on_the_recovered_psgw(context)
    # Trying ssh login through reveal console password
    validate_ssh_login_through_console_password(context, reveal_console_password)


"""
TestRail ID - C57582156	:
    Recover a healthy state PSG
"""


@mark.order(2265)
@mark.recover
@mark.dependency(depends=["test_power_on_the_recovered_psgw"])
def test_recover_healthy_psg(context):
    # Trying to recover healthy (OK and CONNECTED) psg
    wait_for_psg(context, state=State.OK, health_state=HealthState.OK, health_status=HealthStatus.CONNECTED)
    logger.info(f"Recovering psg {context.psgw_name} which is in OK/WARNING and CONNECTED state")
    response = recover_protection_store_gateway_vm(
        context,
        recover_psgw_name=f"recover_{context.psgw_name}_error",
        return_response=True,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_RECOVER_OK_CONNECTED_PSG,
    )


"""
TestRail ID - C57582155	:
    Recover a PSG with the same name to same vCenter
"""


@mark.order(2270)
@mark.recover
@mark.dependency(depends=["test_power_on_the_recovered_psgw"])
def test_recover_psg_with_same_name(context):
    # Trying to recover psg with same psg name

    logger.info(f"Recovering psg with same name as {context.psgw_name}")
    response = recover_protection_store_gateway_vm(
        context,
        recover_psgw_name=context.psgw_name,
        return_response=True,
    )
    validate_psgw_error_messages(
        response,
        expected_status_code=codes.bad_request,
        expected_error=ERROR_MESSAGE_CREATE_PSG_VM_EXISTS,
    )


"""
TestRail ID - C57582141
    Recover a PSG contains multiple cloud store
TestRail ID - C57582143
    Recover PSG back to back with multiple cloud store
"""


@mark.order("second_to_last")
@mark.recover
@mark.dependency()
def test_recover_psg_with_multplie_cloud_stores(context, vm_deploy):
    select_or_create_protection_store_gateway_vm(context)
    unassign_protecion_policy_from_all_vms(context)
    delete_unassinged_protection_policy(context)
    create_protection_template_with_multiple_cloud_regions(
        context, cloud_regions=[AzureLocations.AZURE_southeastasia, AwsStorageLocation.AWS_US_EAST_2]
    )
    time.sleep(10)
    assign_protection_template_to_vm(context)
    run_backup(context, backup_type=BackupTypeScheduleIDs.schedule_id_4)
    # As part of C56958364, Recover PSG back to back so using looping here.
    for counter in range(1, 3):
        logger.info("Started delete and recover PSG for " + str(counter) + " time...")
        # Delete PSG VM from vCenter to simulate PSG disaster
        delete_protection_store_gateway_vm_from_vcenter(context, force=True)

        # Wait for PSG state become Unknown and health state/status become Unknown/Disconnecte
        wait_for_psg(
            context, state=State.UNKNOWN, health_state=HealthState.UNKNOWN, health_status=HealthStatus.DISCONNECTED
        )

        # As per the design, PSG Cloud stores needs 15 minutes of idle time before we attempt to "/recover"
        logger.info("PSG Cloud store needs 15min of idle time before attempting '/recover' operation. Sleeping 15mins")
        time.sleep(15 * 60)

        # Recover PSG VM & Validate PSG
        recover_protection_store_gateway_vm(
            context,
            recover_psgw_name=f"recover_{context.psgw_name}_{counter}",
        )
        validate_protection_store_gateway_vm(context)
        logger.info("Completed delete and recover PSG for " + str(counter) + " time...")


"""
TestRail ID - C57582161	:
    Delete recovered PSG whose VM removed from the vCenter
"""


@mark.order(2280)
@mark.recover
@mark.dependency(depends=["test_recover_psg_happy_path"])
def test_delete_recovered_PSG_when_psgw_vm_already_deleted(context):
    delete_protection_store_gateway_vm_from_vcenter(context, force=True)
    delete_protection_store_gateway_vm(context)
    logger.info("Deletion of recovered psgw from dscc successful after deleting the psgw from vcenter")


"""
TestRail ID - C57582163	:
    Unregister vCenter when recovered PSG contains few local/cloud backups
"""


@mark.order("last")
@mark.recover
@mark.dependency(depends=["test_recover_psg_with_multplie_cloud_stores"])
def test_unregister_vcenter_recovered_psg_local_cloud_backups(context):
    unregister_vcenter(context)
    logger.info("Unregsiter the vCenter successfully with recovered psg contains local and cloud backup")
    add_vcenter(context)
    logger.info("Re-regsiter the vCenter successfully after unregistered")
