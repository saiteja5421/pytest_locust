"""
    C57581996 - Monitor the Cloud Protection Pool status

    C57581999 - Monitor Local Store usage after backup -frequency at which usage is polled

    C57582000 - Monitor Cloud Store usage after backup -frequency at which usage is polled
"""

import logging
from pytest import fixture, mark
from tests.catalyst_gateway_e2e.test_context import Context
from lib.common.enums.backup_type_schedule_ids import BackupTypeScheduleIDs
from tests.steps.vm_protection.protection_template_steps import (
    assign_protection_template_to_vm,
    create_protection_template,
    unassign_protecion_policy_from_vm,
)
from tests.steps.vm_protection.psgw_steps import (
    create_protection_store_gateway_vm,
    validate_protection_store_gateway_vm,
)
from tests.steps.vm_protection.backup_steps import (
    run_backup_and_check_usage,
)
from tests.steps.vm_protection.vmware_steps import VMwareSteps
from lib.common.enums.aws_regions import AwsStorageLocation
from lib.dscc.backup_recovery.vmware_protection.protection_store_gateway.api.catalyst_gateway import CatalystGateway
from tests.steps.vm_protection.common_steps import (
    perform_cleanup,
    execute_cmd_in_vm,
)

logger = logging.getLogger()


@fixture(scope="module")
def context():
    test_context = Context()
    yield test_context
    logger.info("Teardown Start".center(20, "*"))
    perform_cleanup(test_context, clean_large_vm=True)
    logger.info("Teardown Complete".center(20, "*"))


"""
C57581996 - Monitor the Cloud Protection Pool status
"""


@mark.order(2950)
@mark.dependency()
def test_monitor_protection_pool_status(context, vm_deploy):
    create_protection_store_gateway_vm(context)
    validate_protection_store_gateway_vm(context)
    atlas = CatalystGateway(context.user)
    copy_pools = atlas.get_protection_stores()
    psgw_id = atlas.get_catalyst_gateway_id(context)
    local_copy_pool_id = atlas.get_local_copy_pool(context, psgw_id, copy_pools)
    assert local_copy_pool_id is not None, "Local copy pool not found"
    logger.info(f"Local protection store created with id: {local_copy_pool_id}")
    vcenter_control = VMwareSteps(context.vcenter_name, context.vcenter_username, context.vcenter_password)
    create_protection_template(context, cloud_region=AwsStorageLocation.AWS_EU_NORTH_1)
    assign_protection_template_to_vm(context)
    copy_pools = atlas.get_protection_stores()
    cloud_copy_pool_id = atlas.get_cloud_copy_pool(
        context,
        context.psgw_name,
        psgw_id,
        copy_pools,
        context.user,
        cloud_region=AwsStorageLocation.any,
        create_cloud_pool=False,
    )
    assert cloud_copy_pool_id is not None, "Cloud copy pool not found"
    logger.info(f"Cloud protection store created with id: {cloud_copy_pool_id}")

    unassign_protecion_policy_from_vm(context)
    vcenter_control.delete_vm(context.vm_name)


"""
C57581999 - Monitor Local Store usage after backup -frequency at which usage is polled

"""


logger.warning(
    "This testcase requires multiple vms deployment with large data on vm, please make sure to have vm template with large data on test environment"
)


@mark.order(2960)
@mark.dependency(depends=["test_monitor_protection_pool_status"])
# Creating large vms from template
def test_monitor_local_store_usage_after_backup(context, deploy_multiple_vm_large_data):
    # Assigning protection policy, running backups and checking its usage
    for vm in context.large_size_data_vm_name_list:
        context.vm_name = vm
        context.vm_id = context.hypervisor_manager.get_id(context.vm_name, context.hypervisor_manager.get_vms())
        assign_protection_template_to_vm(context)
        run_backup_and_check_usage(context=context, backup_type=BackupTypeScheduleIDs.local)

    # Logging into vms, generating IOs of size 4g, running backups and checking its usage
    for vm in context.large_size_data_vm_name_list:
        vcenter_control = VMwareSteps(context.vcenter_name, context.vcenter_username, context.vcenter_password)
        vm_ip = vcenter_control.get_vm_ip_by_name(vm)
        logger.info(f"vm details - name:{vm} ip:{vm_ip}")
        context.vm_name = vm
        context.vm_id = context.hypervisor_manager.get_id(context.vm_name, context.hypervisor_manager.get_vms())
        # using customized  vm template - largevm_api, having existing data of size - 5GB in /usr/xtngio folder
        # using dmcore tool and writing 4g data in folder /usr/newio/
        cmd = './dmcore Command=Write "DMExecSet=Nas" "DMVerificationMode=MD5" "ExportFileName=/usr/newio/testdmcore1" "WriteT=4g" "WriteI=256k"'
        output = execute_cmd_in_vm(cmd, vm_ip, username=context.large_vm_username, password=context.large_vm_password)
        assert 'ReturnMessage="Success"' in output, f"Failing to write data file to VM: {vm_ip}"
        run_backup_and_check_usage(context=context, backup_type=BackupTypeScheduleIDs.local)


"""
C57582000 - Monitor Cloud Store usage after backup -frequency at which usage is polled

"""


logger.warning(
    "This testcase requires multiple vms deployment with large data on vm, please make sure to have vm template with large data on test environment"
)


@mark.order(2970)
@mark.dependency(depends=["test_monitor_local_store_usage_after_backup"])
def test_monitor_cloud_store_usage_after_backup(context):
    # Using existing vms for which protection policy is already assigned, running backups and checking its usage
    for vm in context.large_size_data_vm_name_list:
        vcenter_control = VMwareSteps(context.vcenter_name, context.vcenter_username, context.vcenter_password)
        context.vm_name = vm
        context.vm_id = context.hypervisor_manager.get_id(context.vm_name, context.hypervisor_manager.get_vms())
        run_backup_and_check_usage(context=context, backup_type=BackupTypeScheduleIDs.cloud)

    # Logging into vms, generating IOs of size 4g, running backups and checking its usage
    for vm in context.large_size_data_vm_name_list:
        vcenter_control = VMwareSteps(context.vcenter_name, context.vcenter_username, context.vcenter_password)
        vm_ip = vcenter_control.get_vm_ip_by_name(vm)
        logger.info(f"vm details - name:{vm} ip:{vm_ip}")
        context.vm_name = vm
        context.vm_id = context.hypervisor_manager.get_id(context.vm_name, context.hypervisor_manager.get_vms())
        # using customized  vm template - largevm_api, having existing data of size - 5GB + 4g in /usr/xtngio folder
        # using dmcore tool and writing again 4g data in folder /usr/newio/
        cmd = './dmcore Command=Write "DMExecSet=Nas" "DMVerificationMode=MD5" "ExportFileName=/usr/newio/testdmcore1" "WriteT=4g" "WriteI=256k"'
        output = execute_cmd_in_vm(cmd, vm_ip, username=context.large_vm_username, password=context.large_vm_password)
        assert 'ReturnMessage="Success"' in output, f"Failing to write data file to VM: {vm_ip}"
        run_backup_and_check_usage(context=context, backup_type=BackupTypeScheduleIDs.cloud)

    # perform_clean(clean_large_vm=True) will clean up all backups and large vms
